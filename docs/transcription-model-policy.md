# Transcription model policy

SubBurn's default transcription catalog is small and fixed. Models are downloaded only after explicit user action, installed to app-managed local storage, pinned to an immutable upstream revision, validated before being marked ready, and then reused locally without another network download.

## Current audited default catalog

The built-in catalog uses six multilingual Faster-Whisper/CTranslate2 model families:

- large-v3
- turbo
- medium
- small
- base
- tiny

Each model has an immutable repository revision recorded in `src/subburn/app.py`. Inference loads the local prepared directory with `local_files_only=True`; it does not pass a mutable model alias to Faster-Whisper at transcription time.

## Language selection

SubBurn validates against OpenAI Whisper's official 100-language token set. Examples:

- `en` - English
- `ar` - Arabic
- `he` - Hebrew
- `zh` - Chinese / Mandarin
- `yue` - Cantonese

Country codes such as `cn` and ambiguous codes such as `ch` are not Whisper language tokens and are rejected before inference.

The **Fixed language code** mode forces one supported language. **Allowed languages (detect changes)** constrains per-context detection to the selected supported codes. **Auto multilingual** leaves language detection unconstrained.

## Language-specialized models

A specialized model must not be silently selected merely because the user chose a language. It may be added only after all of the following are documented and tested:

1. immutable model revision and exact files;
2. model/code/data license and redistribution implications;
3. CTranslate2/Faster-Whisper compatibility;
4. install size, CPU/GPU requirements and quantization;
5. representative benchmark corpus for the target language/dialect;
6. WER/CER comparison against SubBurn's multilingual baseline;
7. failure/recovery/install-once tests;
8. limitations such as degraded language detection or translation;
9. real inference acceptance on supported platforms.

### English

OpenAI publishes official English-only `tiny.en`, `base.en`, `small.en`, and `medium.en` variants. OpenAI states the English-only variants tend to perform better than the corresponding multilingual models, especially tiny/base. These are possible candidates for a future audited English-specialized catalog.

### Hebrew

`ivrit-ai/whisper-large-v3-ct2` and `ivrit-ai/whisper-large-v3-turbo-ct2` are Hebrew-specific CTranslate2 candidates worth testing. Their model cards state that the fine-tuning is intended for mostly-Hebrew audio and that language detection/translation capabilities are degraded. If added, Hebrew must be explicitly forced and the model must never replace multilingual Auto mode silently.

### Arabic

Community Arabic fine-tunes exist, including CTranslate2 builds for multi-dialect Arabic. Their reported quality varies by dialect and use case; some model cards explicitly report that baseline Whisper large-v3 remains better for certain MSA/broadcast workloads. No Arabic community model should become a default without an independent benchmark.

### Chinese / Mandarin / Cantonese

Whisper itself supports `zh` and `yue`. Community Mandarin/Traditional-Chinese CTranslate2 fine-tunes exist, but they are not equivalent to an official language-specific OpenAI model and require independent CER benchmarking and provenance review before inclusion.

## Release gate still outstanding

The current execution container cannot resolve `huggingface.co`, so it cannot honestly perform the multi-gigabyte real upstream download and inference acceptance. The controlled stress suite exercises all six model identities, concurrent preparation, interrupted downloads, staging cleanup, progress, durable install markers, stale revision repair, cross-process restart reuse, and local-only inference behavior. A network-enabled pre-release environment must still download each pinned model for real and run representative audio through it before a stable release claim.
