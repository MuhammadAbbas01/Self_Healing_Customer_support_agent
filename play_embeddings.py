from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("all-MiniLM-L6-v2")

list = ["authentication failed, unauthorized", "how to bake a chocolate cake", "authentication failed, unauthorized"]

sentences = [
    "my api key gives 401 error",
    "authentication failed, unauthorized",
    "how to bake a chocolate cake",
]

embeddings = model.encode(sentences)
print(embeddings.shape)

print(util.cos_sim(embeddings[0], embeddings[1]))
print(util.cos_sim(embeddings[0], embeddings[2]))