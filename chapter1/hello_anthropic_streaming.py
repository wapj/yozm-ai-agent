import anthropic
import rich

client = anthropic.Anthropic()

prompt = "anthropic 발음은 앤트로픽이 맞나요? 앤스로픽이 맞나요?"
with client.messages.stream(
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
    model="claude-3-5-haiku-20241022",
) as stream:
    for event in stream:
        if event.type == "text":
            print(event.text, end="", flush=True)
    print()
    rich.print(stream.get_final_message())
