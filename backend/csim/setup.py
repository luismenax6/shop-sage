from setuptools import Extension, setup

setup(
    name="csim",
    version="0.1.0",
    description="Cosine similarity C extension for shop-sage RAG retrieval",
    ext_modules=[
        Extension(
            "csim",
            sources=["cosine.c"],
            extra_compile_args=["-O3"],  # let the compiler optimize the hot loop
        )
    ],
)
