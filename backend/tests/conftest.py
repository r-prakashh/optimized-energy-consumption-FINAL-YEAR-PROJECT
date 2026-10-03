# Load onnxruntime (bill OCR) before LightGBM's OpenMP runtime — see app/main.py.
try:
    import onnxruntime  # noqa: F401
except ImportError:
    pass
