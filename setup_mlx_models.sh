#!/bin/bash

# ABOUTME: Download and cache MLX Whisper + translation models locally
# ABOUTME: Avoids long first-run delays by pre-downloading models with smart caching

show_help() {
    cat << EOF
╔════════════════════════════════════════════════════════════════╗
║          MLX Whisper & Translation Model Setup                 ║
╚════════════════════════════════════════════════════════════════╝

USAGE:
  ./setup_mlx_models.sh [OPTIONS]

OPTIONS:
  --help, -h                Show this help message

  WHISPER MODELS:
    --whisper all           Download all Whisper models (default)
    --whisper small         Download small model (244MB, fast)
    --whisper medium        Download medium model (769MB, accurate)
    --whisper large         Download large-v3 model (2.9GB, highest accuracy)
    --whisper small,medium  Download multiple (comma-separated, no spaces)

  TRANSLATION MODELS:
    --translation ur        Download Urdu translation
    --translation hi        Download Hindi translation
    --translation zh        Download Chinese translation
    --translation hi,ur,zh  Download multiple (comma-separated, no spaces)
                           Available: hi (Hindi), ur (Urdu), zh (Chinese)

EXAMPLES:
  ./setup_mlx_models.sh                    # Default: small, medium, large speech-to-text only
  ./setup_mlx_models.sh --whisper small    # Download only small Whisper model
  ./setup_mlx_models.sh --translation ur   # small, medium, large Whisper + Urdu translation
  ./setup_mlx_models.sh --translation hi,zh
                                           # small, medium, large Whisper + Hindi + Chinese
  ./setup_mlx_models.sh --whisper small --translation ur,hi
                                           # Small Whisper + Urdu + Hindi translations

DISK SPACE REQUIRED:
  Whisper:
    - small (244MB): ~300MB
    - medium (769MB): ~850MB
    - large-v3 (2.9GB): ~3.2GB
  Translation (per model):
    - Each translation model: ~100-200MB
    - Urdu: ~150MB

Cache location: ~/.cache/huggingface/hub/

EOF
}

# Initialize defaults
whisper_models=()
translation_langs=()
use_defaults=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --whisper)
            use_defaults=false
            if [ -z "$2" ]; then
                echo "Error: --whisper requires an argument (all, small, medium, large, or comma-separated list)"
                exit 1
            fi
            if [ "$2" = "all" ]; then
                whisper_models=("small" "medium" "large-v3")
            else
                # Split by comma and add to array
                IFS=',' read -ra whisper_models <<< "$2"
            fi
            shift 2
            ;;
        --translation)
            use_defaults=false
            if [ -z "$2" ]; then
                echo "Error: --translation requires an argument (urdu, all, or comma-separated list)"
                exit 1
            fi
            if [ "$2" = "all" ]; then
                translation_langs=("hi" "ur" "ar" "zh" "ja")
            else
                # Split by comma and add to array
                IFS=',' read -ra translation_langs <<< "$2"
            fi
            shift 2
            ;;
        *)
            echo "Error: Unknown option $1"
            show_help
            exit 1
            ;;
    esac
done

# Set defaults if no arguments provided
if [ "$use_defaults" = true ]; then
    whisper_models=("small" "medium" "large-v3")
    # No translation models by default - user must specify with --translation
fi

# If only --whisper was specified but not --translation, keep translation empty (no translation)
if [ ${#whisper_models[@]} -gt 0 ] && [ ${#translation_langs[@]} -eq 0 ]; then
    # Do nothing - translation models stay empty
    :
fi

# If only --translation was specified but not --whisper, add default all Whisper models
if [ ${#whisper_models[@]} -eq 0 ] && [ ${#translation_langs[@]} -gt 0 ]; then
    whisper_models=("small" "medium" "large-v3")
fi

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          MLX Whisper & Translation Model Setup                 ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Models to download:"
echo "  Whisper models: ${whisper_models[*]}"
echo "  Translation languages: ${translation_langs[*]}"
echo ""
echo "Cache location: ~/.cache/huggingface/hub/"
echo ""

# Activate virtual environment
cd "$(dirname "$0")"
source venv/bin/activate

# Check if required packages are installed
if ! python -c "import mlx_whisper" 2>/dev/null; then
    echo "Error: mlx-whisper not installed"
    echo "Run: pip install mlx-whisper"
    exit 1
fi

if ! python -c "import transformers" 2>/dev/null; then
    echo "Error: transformers not installed"
    echo "Run: pip install transformers"
    exit 1
fi

echo "Starting model download..."
echo ""

# Function to get whisper model display name
get_whisper_name() {
    case "$1" in
        tiny) echo "tiny (39MB, very fast)" ;;
        base) echo "base (140MB, fast)" ;;
        small) echo "small (244MB, fast & accurate)" ;;
        medium) echo "medium (769MB, high accuracy)" ;;
        large-v3) echo "large-v3 (2.9GB, highest accuracy)" ;;
        large) echo "large-v3 (2.9GB, highest accuracy)" ;;
        *) echo "$1" ;;
    esac
}

# Function to get translation model path
get_translation_model() {
    case "$1" in
        hi) echo "Helsinki-NLP/opus-mt-hi-en:Hindi→English" ;;
        ur) echo "Helsinki-NLP/opus-mt-ur-en:Urdu→English" ;;
        zh) echo "Helsinki-NLP/opus-mt-zh-en:Chinese→English" ;;
        *) echo "" ;;
    esac
}

# Function to get language name
get_lang_name() {
    case "$1" in
        hi) echo "Hindi" ;;
        ur) echo "Urdu" ;;
        zh) echo "Chinese" ;;
        *) echo "$1" ;;
    esac
}

failed=0
cache_dir="$HOME/.cache/huggingface/hub"

echo "═══════════════════════════════════════════════════════════════"
echo "1️⃣  WHISPER MODELS (Speech-to-Text)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

for model in "${whisper_models[@]}"; do
    # Normalize large to large-v3
    if [ "$model" = "large" ]; then
        model="large-v3"
    fi

    model_name=$(get_whisper_name "$model")
    model_cache="models--mlx-community--whisper-${model}-mlx"

    if [ -d "$cache_dir/$model_cache" ]; then
        echo "✓ $model_name (already cached, skipping)"
        echo ""
        continue
    fi

    echo "📥 Downloading $model_name..."
    echo "   (This may take a few minutes depending on internet speed)"

    USE_MLX_WHISPER=true MLX_WHISPER_MODEL="$model" python -c "
import mlx_whisper
import os
try:
    # This will download to cache
    result = mlx_whisper.transcribe('/dev/null', path_or_hf_repo='mlx-community/whisper-${model}-mlx')
    print('✓ ${model} downloaded successfully')
except Exception as e:
    # Expected error (invalid audio), but model is downloaded
    if 'not found' not in str(e).lower() and 'connection' not in str(e).lower():
        print('✓ ${model} downloaded successfully')
    else:
        print('✗ Failed to download ${model}: ' + str(e))
        exit(1)
" 2>&1 || {
        echo "✗ Failed to download $model"
        failed=$((failed + 1))
        continue
    }

    echo ""
done

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "2️⃣  TRANSLATION MODELS (Text-to-English)"
echo "═══════════════════════════════════════════════════════════════"
echo ""

for lang in "${translation_langs[@]}"; do
    translation_model=$(get_translation_model "$lang")
    if [ -z "$translation_model" ]; then
        echo "✗ Unknown language code: $lang"
        echo "   Available: hi (Hindi), ur (Urdu), zh (Chinese)"
        failed=$((failed + 1))
        continue
    fi

    model_name="${translation_model%%:*}"
    lang_pair="${translation_model##*:}"

    # Check if model is already cached
    cache_model=$(echo "$model_name" | sed 's|/|--|g')
    model_cache="models--$cache_model"

    if [ -d "$cache_dir/$model_cache" ]; then
        echo "✓ $lang_pair (already cached, skipping)"
        echo ""
        continue
    fi

    echo "📥 Downloading $lang_pair translation model..."
    echo "   (Model: $model_name)"

    python -c "
from transformers import pipeline
try:
    # Load the translation model to cache it
    translator = pipeline('translation', model='$model_name', device=-1)
    print('✓ $lang_pair model downloaded successfully')
except Exception as e:
    print('✗ Failed to download $lang_pair model: ' + str(e))
    exit(1)
" 2>&1 || {
        echo "✗ Failed to download $lang_pair"
        failed=$((failed + 1))
        continue
    }

    echo ""
done

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
if [ $failed -eq 0 ]; then
    echo "║                    ✓ SUCCESS!                                 ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "All models downloaded and cached successfully!"
    echo ""
    echo "Cache location: ~/.cache/huggingface/hub/"
    echo "Total cache size:"
    du -sh ~/.cache/huggingface/hub/ 2>/dev/null || echo "(Run 'du -sh ~/.cache/huggingface/hub/' to check size)"
    echo ""
    echo "✅ You can now use MLX Whisper with local transcription:"
    echo ""
    echo "Usage:"
    for model in "${whisper_models[@]}"; do
        echo "  ./run.sh --use-local $model"
    done
    echo ""
    if [ ${#translation_langs[@]} -gt 0 ]; then
        echo "Supported translation languages:"
        for lang in "${translation_langs[@]}"; do
            echo "  - $(get_lang_name "$lang")"
        done
        echo ""
        echo "Try recording in one of these languages!"
        echo "Audio will be transcribed and translated to English locally."
    fi
else
    echo "║                    ✗ FAILED                                   ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Some models failed to download. Please check your internet connection."
    exit 1
fi
