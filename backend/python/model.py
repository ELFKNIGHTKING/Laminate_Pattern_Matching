from PIL import Image
import torch
import clip
from typing import List, cast

device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

def get_image_embedding(image_path: str) -> List[float]:
    """
    Converts an image to a normalized embedding vector.
    """
    img = Image.open(image_path).convert("RGB")
    tensor = cast(torch.Tensor, preprocess(img))
    tensor = tensor.unsqueeze(0).to(device)

    with torch.no_grad():
        embedding = model.encode_image(tensor)
        embedding /= embedding.norm(dim=-1, keepdim=True)

    return embedding.squeeze(0).cpu().tolist()

def is_laminate_image(image_path: str) -> bool:
    """
    Uses CLIP to check if the image is likely a laminate pattern,
    using prompt engineering for simple negative filtering.
    Returns True if laminate, False otherwise.
    """
    img = Image.open(image_path).convert("RGB")
    tensor = cast(torch.Tensor, preprocess(img))
    tensor = tensor.unsqueeze(0).to(device)

    text = clip.tokenize([
        "a laminate pattern",
        "a person",
        "a meme",
        "a room",
        "a random object"
    ]).to(device)

    with torch.no_grad():
        image_features = model.encode_image(tensor)
        text_features = model.encode_text(text)
        image_features /= image_features.norm(dim=-1, keepdim=True)
        text_features /= text_features.norm(dim=-1, keepdim=True)
        similarity = (100.0 * image_features @ text_features.T).softmax(dim=-1)
        probs = similarity.squeeze().tolist()

    labels = ["laminate", "person", "meme", "room", "random"]
    top_label, confidence = max(zip(labels, probs), key=lambda x: x[1])

    # You can tighten or relax the confidence threshold as needed!
    return top_label == "laminate" and confidence > 0.4
