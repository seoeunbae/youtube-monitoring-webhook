import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def generate(file_uri, prompt):
  client = genai.Client(
      vertexai=True,
      project=os.getenv('GCP_PROJECT'),
      location="global",
  )

  msg1_text1 = types.Part.from_text(text=prompt)
  msg1_video1 = types.Part.from_uri(
      file_uri=file_uri,
      mime_type="video/*",
  )

  model = "gemini-2.5-pro"
  contents = [
    types.Content(
      role="user",
      parts=[
        msg1_text1,
        msg1_video1
      ]
    ),
  ]

  generate_content_config = types.GenerateContentConfig(
    temperature = 1,
    top_p = 0.95,
    seed = 0,
    max_output_tokens = 65535,
    safety_settings = [types.SafetySetting(
      category="HARM_CATEGORY_HATE_SPEECH",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_DANGEROUS_CONTENT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
      threshold="OFF"
    ),types.SafetySetting(
      category="HARM_CATEGORY_HARASSMENT",
      threshold="OFF"
    )],
    thinking_config=types.ThinkingConfig(
      thinking_budget=-1,
    ),
  )
  response = client.models.generate_content(
    model = model,
    contents = contents,
    config = generate_content_config,
    )
  return response.text
