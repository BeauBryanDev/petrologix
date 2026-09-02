from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Aegis-Geo-Mind"
    debug: bool = False

    # Uploads
    max_upload_mb: int = 50

 
    # Only the two demo wells are kept here 
    las_sample_dir: str = str(Path(__file__).resolve().parents[2] / "data" / "samples")

    # Lithology model. Leave model_dir unset to use the version bundled inside the
    # petrologix wheel; point PETROLOGIX_MODELS_DIR at a directory containing
    # <version>/lithology_model.pkl to serve a different one without reinstalling.
    petrologix_models_dir: str | None = None

    # Minimum zone thickness (metres) when collapsing predictions into intervals.
    min_interval_thickness_m: float = 0.5

    # Geologist LLM — Qwen2.5-7B QLoRA (4-bit) on a Hugging Face Gradio Space,
    # T4 GPU, called over HTTP. 
    #
    # The Space exposes a single endpoint: respond(message) -> response.
    # A token is optional for a public Space 
    hf_llm_endpoint: str = "https://beaunix-aegis-geo-mind-demo.hf.space"
    hf_llm_api_name: str = "/chat"
    hf_token: str | None = None
    
    # Anthropic LLM, Now this is the default LLM Provider
    anthropic_model: str = "claude-sonnet-5"
    anthropic_api_key: str | None = None

    # max_tokens caps thinking + answer together, so a low cap truncates the
    # answer mid-sentence. 4096 leaves room for a full lithology assessment;
    # stay under ~16000 while the client is non-streaming (HTTP timeouts).
    anthropic_max_tokens: int = 2048
    # Sonnet 5 runs adaptive thinking when the parameter is omitted, and that
    # spends the same budget as the answer. Off by default: the reasoning is
    # never shown and the geology prompt does not need it.
    anthropic_thinking: bool = False

    # A cold T4 Space takes 1-3 minutes to boot; generation adds seconds more.
    llm_read_timeout_s: float = 300.0
    llm_connect_timeout_s: float = 15.0
    # Nudge the Space awake at startup so the first user does not pay the boot.
    llm_warm_on_startup: bool = True

    # RAG — geology corpus in Qdrant Cloud, read-only from this backend.
    # QDRANT_CLUSTER_ENDPOINT_REST is what the Qdrant Cloud console hands you;
    # accepted as an alias so the .env does not have to be rewritten.
    qdrant_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("QDRANT_URL", "QDRANT_CLUSTER_ENDPOINT_REST"),
    )
    qdrant_api_key: str | None = None
    qdrant_collection: str = "geo_corpus"
    qdrant_timeout_s: float = 20.0

    # Query embeddings: BAAI/bge-large-en-v1.5, 1024 dims, over HTTP for the same
    # reason the LLM is — no torch in this image. The endpoint MUST serve the
    # same model the collection was built with, and must apply sentence pooling.
    embedding_endpoint: str | None = None
    # Falls back to hf_token when unset.
    embedding_token: str | None = None
    embedding_timeout_s: float = 30.0
    # bge wants this instruction on queries only; passages are embedded bare.
    embedding_query_prefix: str = (
        "Represent this sentence for searching relevant passages: "
    )

    # Retrieval. The threshold is cosine similarity — below ~0.5 bge returns
    # topically unrelated text, which is worse than no context at all.
    rag_enabled: bool = True
    rag_top_k: int = 5
    rag_score_threshold: float = 0.5
    rag_max_chars_per_passage: int = 1500
    # Fetch k * this, then drop near-duplicates down to k.
    rag_overfetch: int = 3
    # section_title is a concatenation of every heading on the page; trim it so a
    # citation stays readable.
    rag_max_section_chars: int = 80
    
    # EIA API KEY Used to get the EIA data
    EIA_API_KEY: str | None = None


settings = Settings()
