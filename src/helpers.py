import os

from IPython.display import Markdown, display
from azure.ai.translation.document import SingleDocumentTranslationClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from openai import OpenAI
from rich.markdown import Markdown

load_dotenv(override=True)


def get_ollama_client():
    return OpenAI(
        base_url=os.getenv('OLLAMA_ENDPOINT'),
        api_key=os.getenv('OLLAMA_API_KEY')
    )


def get_azure_client():
    return OpenAI(
        base_url=os.getenv('AZURE_OPENAI_ENDPOINT'),
        api_key=os.getenv('AZURE_API_KEY')
    )


# Chat

class LLMTruncatedError(RuntimeError):
    """Raised when the model's response was cut off before completion."""


def chat(msg, model, client_type='azure', display_output=False, codex=False, system=None, max_output_tokens=None):
    if client_type == 'azure':
        client = get_azure_client()
    elif client_type == 'ollama':
        client = get_ollama_client()
    else:
        raise NotImplemented("No.")
    
    if codex:
        kwargs = {"model": model, "input": msg}
        if system is not None:
            kwargs["instructions"] = system
        if max_output_tokens is not None:
            kwargs["max_output_tokens"] = max_output_tokens
        response = client.responses.create(**kwargs)
        if getattr(response, "status", None) == "incomplete":
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", "unknown") if details is not None else "unknown"
            raise LLMTruncatedError(
                f"Response truncated before completion (reason: {reason}). "
                f"Increase max_output_tokens or shorten the input."
            )
        answer = response.output_text
    else:
        messages = []
        if system is not None:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": msg})
        completion_kwargs = {"model": model, "messages": messages}
        if max_output_tokens is not None:
            completion_kwargs["max_tokens"] = max_output_tokens
        response = client.chat.completions.create(**completion_kwargs)
        finish_reason = getattr(response.choices[0], "finish_reason", None)
        if finish_reason == "length":
            raise LLMTruncatedError(
                "Response truncated before completion (finish_reason=length). "
                "Increase max_output_tokens or shorten the input."
            )
        answer = response.choices[0].message.content
    
    if display_output:
        display(Markdown(answer))
    return answer


def qwen_coder_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="qwen2.5-coder:7b", client_type='ollama', display_output=display_output, system=system, max_output_tokens=max_output_tokens)


def gemma4_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="gemma4:e4b", client_type='ollama', display_output=display_output, system=system, max_output_tokens=max_output_tokens)


def gemma3_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="gemma3:4b", client_type='ollama', display_output=display_output, system=system, max_output_tokens=max_output_tokens)


def nemo_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="mistral-nemo:12b", client_type='ollama', display_output=display_output, system=system, max_output_tokens=max_output_tokens)


def llama_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="llama3.1:8b", client_type='ollama', display_output=display_output, system=system, max_output_tokens=max_output_tokens)


def gpt_mini_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="gpt-4.1-mini", client_type='azure', display_output=display_output, system=system, max_output_tokens=max_output_tokens)


def gpt_41_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="gpt-4.1", client_type='azure', display_output=display_output, codex=True, system=system, max_output_tokens=max_output_tokens)


def gpt_codex_chat(msg, display_output=False, system=None, max_output_tokens=None):
    return chat(msg, model="gpt-5.3-codex", client_type='azure', display_output=display_output, codex=True, system=system, max_output_tokens=max_output_tokens)


# Translation

def get_translator_client():
    return SingleDocumentTranslationClient(
        os.getenv('AZURE_TRANSLATOR_ENDPOINT'),
        AzureKeyCredential(os.getenv('AZURE_TRANSLATOR_API_KEY'))
    )


# limits as of 2026-05-01
# https://learn.microsoft.com/en-us/azure/ai-services/translator/service-limit
MAX_MB_SYNCHRONOUS = 10
MAX_MB_BATCH = 40
SYNC_DOCUMENT_TRANSLATION_MAX_BYTES = MAX_MB_SYNCHRONOUS * 1024 * 1024


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def translate_document_bytes(data, source_language="en", filename="document.docx", content_type=DOCX_MIME):
    size = len(data)
    if size > SYNC_DOCUMENT_TRANSLATION_MAX_BYTES:
        raise NotImplementedError(
            f"document is {size / 1024 / 1024:.1f} MB; "
            f"SingleDocumentTranslationClient caps at {MAX_MB_SYNCHRONOUS} MB. "
            f"Use the async batch client for larger files (up to {MAX_MB_BATCH} MB)."
        )
    
    if source_language.lower() == "en":
        target_language = "fr"
    elif source_language.lower() == "fr":
        target_language = "en"
    else:
        raise ValueError("Unsupported language.")
    
    client = get_translator_client()
    response = client.translate(
        target_language=target_language,
        body={"document": (filename, data, content_type)}
    )
    return bytes(response)


def translate_document(file_path, input_language="en"):
    with open(file_path, "rb") as f:
        data = f.read()
    translated = translate_document_bytes(
        data,
        source_language=input_language,
        filename=file_path.name,
    )
    output_file_path = file_path.with_stem(f"{file_path.stem}_translated")
    with open(output_file_path, "wb") as f:
        f.write(translated)
