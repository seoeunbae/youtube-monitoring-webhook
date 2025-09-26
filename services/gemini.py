import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def generate(file_uri, prompt, text):
  client = genai.Client(
      vertexai=True,
      project=os.getenv('GCP_PROJECT'),
      location="global",
  )
  msg_text = types.Part(text=text)
  msg_video = types.FileData(
      file_uri=file_uri,
      mime_type="video/*"
  )

  video_meta=types.VideoMetadata(
    start_offset="0.0s",
    end_offset="10.0s",
    fps=1.0
  )

  msg_prompt= types.Part(text=prompt)

  part_vidoe_content = types.Part(
    file_data=msg_video,
    video_metadata=video_meta,
  )
  model = "gemini-2.5-pro"
  # contents = [
  #     types.Content(role="user", parts=[
  #       msg_video,
  #       msg_text,
  #       msg_prompt
  #       ]
  #     )
  # ]
  contents = types.Content(
    role="user",
    parts=[
      part_vidoe_content,
      msg_text,
      msg_prompt
    ]
  )
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
    config = generate_content_config
  )
  print(response.text)
  return response.text
