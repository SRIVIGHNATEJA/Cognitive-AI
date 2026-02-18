#!/usr/bin/env bash
set -e

echo "Setting Ollama environment variables via launchctl..."
launchctl setenv OLLAMA_FLASH_ATTENTION 1
launchctl setenv OLLAMA_KV_CACHE_TYPE q8_0
launchctl setenv OLLAMA_NUM_PARALLEL 1
launchctl setenv OLLAMA_MAX_LOADED_MODELS 1
launchctl setenv OLLAMA_KEEP_ALIVE 60m

echo "Restarting Ollama..."
killall Ollama 2>/dev/null || true
sleep 2

echo "Launching Ollama application..."
open -a Ollama

echo "Waiting for Ollama to become available on port 11434..."
while ! curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama is ready and optimized!"
