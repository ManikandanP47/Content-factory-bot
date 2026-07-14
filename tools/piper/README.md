# Piper male voice (local)

Neural male voice models are downloaded on first use by the pipeline
(`en_US-ryan-high` via Hugging Face).

Manual seed (optional):

```bash
mkdir -p voices
curl -fsSL -L \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx?download=true" \
  -o voices/en_US-ryan-high.onnx
curl -fsSL -L \
  "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/ryan/high/en_US-ryan-high.onnx.json?download=true" \
  -o voices/en_US-ryan-high.onnx.json
```

Large `.onnx` binaries and Piper release archives stay gitignored.
