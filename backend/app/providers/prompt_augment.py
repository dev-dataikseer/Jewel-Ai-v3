def augment_prompt_for_workflow(workflow: str, prompt: str) -> str:
    if workflow == "REFERENCE_STYLE_MATCH":
        return (
            f"{prompt} ATTACHED IMAGES: Image 1 is the client's jewelry product — preserve its design exactly. "
            "Image 2 is the style reference — match its background, lighting, mood, color grading, and photographic feel."
        )
    if workflow in ("JEWELRY_ON_MODEL", "CUSTOMER_TRY_ON"):
        return (
            f"{prompt} ATTACHED IMAGES: Image 1 is the jewelry product. "
            "Image 2 is the model or customer portrait. Composite the jewelry naturally onto the person."
        )
    return prompt
