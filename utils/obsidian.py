from pathlib import Path
from datetime import datetime

from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")


def save_and_link(vault_path: Path, title: str, content: str) -> str:
    """Save markdown file and return link text with related notes."""
    vault_path = Path(vault_path)
    vault_path.mkdir(parents=True, exist_ok=True)
    import re
    # sanitize title for filename
    safe_title = re.sub(r'[\\/*?:"<>|]', "_", title).replace(" ", "_")[:50]
    filename = datetime.now().strftime("%Y%m%d_%H%M%S_") + f"[{safe_title}].md"
    target = vault_path / filename
    target.write_text(f"# {title}\n\n" + content, encoding="utf-8")

    # find similar docs
    texts = []
    files = list(vault_path.glob("*.md"))
    for f in files:
        if f == target:
            continue
        texts.append(f.read_text(encoding="utf-8"))
    if not texts:
        return filename  # no related
    embeddings = model.encode(texts + [content], convert_to_tensor=True)
    sim_scores = util.pytorch_cos_sim(embeddings[-1], embeddings[:-1])[0]
    top_idx = sim_scores.topk(3).indices.tolist()
    links = [files[i].stem for i in top_idx]

    # append links to file
    with target.open("a", encoding="utf-8") as f:
        f.write("\n\n## 関連メモ\n")
        for l in links:
            f.write(f"- [[{l}]]\n")
    return filename
