#!/bin/bash
# Download recommended models for Cerebrum

echo "Downloading Cerebrum models..."
cd "$(dirname "$0")"

# Create models directory
mkdir -p .

# Qwen 2.5 Coder 7B (Q4)
echo "Downloading Qwen 2.5 Coder 7B..."
wget -c https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf

# CodeLlama 7B (Q4)
echo "Downloading CodeLlama 7B..."
wget -c https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf

# DeepSeek Coder 6.7B (Q4)
echo "Downloading DeepSeek Coder 6.7B..."
wget -c https://huggingface.co/TheBloke/deepseek-coder-6.7b-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf

echo "✓ Download complete!"
echo ""
echo "Models downloaded:"
ls -lh *.gguf
