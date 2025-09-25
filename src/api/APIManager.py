class APIManager:
    def __init__(self, enabled, model):
        self.enabled = enabled
        self.model = model

    def getResponse(self, query):
        modelMap = {
            "llama3.1:8b":"meta.llama3-1-8b-instruct-v1:0",
            "mistral:7b":"mistral.mistral-7b-instruct-v0:2",
            "gemma3:4b":"gemma-3-4b-it"
        }

        modelName = modelMap[self.model]

        if self.model == "gemma3:4b":
            from google import genai
            client = genai.Client(api_key="AIzaSyABIyALZkmYwd9Wr0HWckVoDT8ncIpZ9dM")

            response = client.models.generate_content(
                model="gemma-3-4b-it",
                contents=query,
            )

            return response.candidates[0].content.parts[0].text
        else:
            import boto3
            from botocore.exceptions import ClientError

            # Create a Bedrock Runtime client in the AWS Region you want to use.
            client = boto3.client("bedrock-runtime", region_name="us-west-2")

            # Set the model ID, e.g., Llama 3 8b Instruct.
            model_id = modelName

            # Start a conversation with the user message.
            user_message = query
            conversation = [
                {
                    "role": "user",
                    "content": [{"text": user_message}],
                }
            ]

            try:
                # Send the message to the model, using a basic inference configuration.
                response = client.converse(
                    modelId=model_id,
                    messages=conversation,
                    inferenceConfig={"maxTokens": 512, "temperature": 0.5, "topP": 0.9},
                )

                # Extract and print the response text.
                response_text = response["output"]["message"]["content"][0]["text"]
                print(response_text)

            except (ClientError, Exception) as e:
                print(f"ERROR: Can't invoke '{model_id}'. Reason: {e}")
                exit(1)
    
    def __str__(self):
        return f"Enabled: {self.enabled}\nModelo: {self.model}"

