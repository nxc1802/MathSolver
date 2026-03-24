from openai import OpenAI

client = OpenAI(
    base_url="https://ai.megallm.io/v1",
    api_key=os.environ.get("MEGALLM_API_KEY")
)

response = client.chat.completions.create(
    model="gpt-5",
    messages=[
        {"role": "user", "content": "Hello, world!"}
    ]
)