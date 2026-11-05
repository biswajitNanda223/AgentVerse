from pathlib import Path

from decision_rag.claude import ClaudeDecisionModel
from decision_rag.corpus import CorpusTree
from decision_rag.jev import JevDecisionModel
from decision_rag.loaders import load_corpus
from decision_rag.local import LexicalDecisionModel
from decision_rag.models import DecisionModel, DecisionModelError
from decision_rag.navigator import NavigationConfig
from decision_rag.pipeline import DecisionRagPipeline
from decision_rag.sample_corpus import sample_tree
from decision_rag.settings import DecisionRagSettings


def build_model(settings: DecisionRagSettings) -> DecisionModel:
    if settings.backend == "local":
        return LexicalDecisionModel()
    if settings.backend == "claude":
        # The SDK reads ANTHROPIC_API_KEY (or an `ant auth login` profile) from the environment.
        return ClaudeDecisionModel(model=settings.claude_model, effort=settings.claude_effort)
    if settings.api_key is None:
        raise DecisionModelError("DECISION_RAG_API_KEY is required when DECISION_RAG_BACKEND=jev")
    return JevDecisionModel(
        settings.api_key,
        mode=settings.judgement,
        base_url=settings.base_url,
        model=settings.model,
        timeout=settings.timeout_seconds,
    )


def build_tree(settings: DecisionRagSettings) -> CorpusTree:
    if settings.corpus_dir:
        return load_corpus(Path(settings.corpus_dir))
    return sample_tree()


def build_config(settings: DecisionRagSettings) -> NavigationConfig:
    return NavigationConfig(
        keep_topics=settings.keep_topics,
        keep_documents=settings.keep_documents,
        keep_sections=settings.keep_sections,
        keep_passages=settings.keep_passages,
        skip_sections=settings.skip_sections,
        rerank=settings.rerank,
        min_probability=settings.min_probability,
        abstain_below=settings.abstain_below,
        max_candidates_per_call=settings.max_candidates_per_call,
    )


def build_pipeline(settings: DecisionRagSettings) -> DecisionRagPipeline:
    return DecisionRagPipeline(build_tree(settings), build_model(settings), build_config(settings))
