import hashlib

import mlflow
from mlflow.entities import SpanType

from manager_ai.agent.workflow_agent import Agent
from manager_ai.models.conversation import JobStatus, Message


class MLFlowTrackedAgent:
    """
    Wraps Agent with MLflow observability.

    For ClaudeAdapter and InstructorExtractor, mlflow.anthropic.autolog() is
    enabled so that token usage, latency, and model metadata are captured
    automatically as child spans. InstructorExtractor defers instructor.from_anthropic()
    until the first collect() call so the autolog patch is already active by then.

    For PydanticAI (which autolog cannot intercept), the LLM adapter is
    monkey-patched at construction time to wrap calls with explicit mlflow.start_span() traces.

    Each handle_message() call produces:
      - One MLflow run with business metrics (stage, fields collected, etc.)
      - One AGENT trace span containing child LLM/extractor spans with the
        full prompts and responses visible in the MLflow Traces view.
    """

    def __init__(self, agent: Agent, experiment_name: str = "manager-ai") -> None:
        self._agent = agent
        mlflow.set_experiment(experiment_name)
        self._maybe_enable_anthropic_autolog()
        self._patch_llm()
        if self._agent._extractor is not None:
            self._patch_extractor()

    def _maybe_enable_anthropic_autolog(self) -> None:
        from manager_ai.adapters.llm.claude import ClaudeAdapter
        from manager_ai.adapters.extractor.instructor_extractor import InstructorExtractor
        if isinstance(self._agent._llm, ClaudeAdapter) or isinstance(self._agent._extractor, InstructorExtractor):
            import mlflow.anthropic
            mlflow.anthropic.autolog()

    def _patch_llm(self) -> None:
        original_complete = self._agent._llm.complete

        def traced_complete(system_prompt: str, messages: list[Message]) -> str:
            with mlflow.start_span("llm.complete", span_type=SpanType.LLM) as span:
                span.set_inputs(
                    {
                        "system_prompt": system_prompt,
                        "messages": [
                            {"role": m.role, "content": m.content}
                            for m in messages
                        ],
                    }
                )
                result = original_complete(system_prompt, messages)
                span.set_outputs({"response": result})
            return result

        self._agent._llm.complete = traced_complete  # type: ignore[method-assign]

    def _patch_extractor(self) -> None:
        original_collect = self._agent._extractor.collect  # type: ignore[union-attr]

        def traced_collect(messages: list[Message]):
            with mlflow.start_span("extractor.collect", span_type=SpanType.LLM) as span:
                span.set_inputs(
                    {"messages": [{"role": m.role, "content": m.content} for m in messages]}
                )
                reply, data = original_collect(messages)
                span.set_outputs({"reply": reply, "extracted": data.model_dump()})
            return reply, data

        self._agent._extractor.collect = traced_collect  # type: ignore[method-assign]

    def handle_message(self, phone: str, text: str) -> None:
        phone_hash = hashlib.sha256(phone.encode()).hexdigest()[:12]

        pre_state = self._agent._storage.load_thread(phone)
        pre_stage = pre_state.status.value if pre_state else "new"

        with mlflow.start_run(run_name=f"msg-{phone_hash}"):
            mlflow.log_param("phone_hash", phone_hash)
            mlflow.log_param("stage_before", pre_stage)

            with mlflow.start_span("handle_message", span_type=SpanType.AGENT) as span:
                span.set_inputs({"user_message": text, "stage": pre_stage})
                self._agent.handle_message(phone=phone, text=text)
                post_state = self._agent._storage.load_thread(phone)
                if post_state:
                    active_job = post_state.get_job(post_state.active_job_id)
                    span.set_outputs({
                        "stage_after": post_state.status.value,
                        "history_length": len(post_state.history),
                        "job_status": active_job.status.value if active_job else "none",
                    })

            post_state = self._agent._storage.load_thread(phone)
            if post_state:
                active_job = post_state.get_job(post_state.active_job_id)
                mlflow.log_param("stage_after", post_state.status.value)
                mlflow.log_metric("history_length", len(post_state.history))
                mlflow.log_metric(
                    "active_jobs",
                    float(
                        sum(
                            1
                            for job in post_state.jobs
                            if job.status
                            not in {JobStatus.CLOSED, JobStatus.DISQUALIFIED, JobStatus.ABANDONED}
                        )
                    ),
                )
                if active_job is not None:
                    mlflow.log_param("job_status", active_job.status.value)
                    mlflow.log_metric(
                        "fields_collected",
                        sum([
                            bool(active_job.contact_name),
                            bool(active_job.scope.address),
                            bool(active_job.scope.city),
                            bool(active_job.scope.installation_type),
                            bool(active_job.scope.has_complete_net_area()),
                        ]),
                    )
