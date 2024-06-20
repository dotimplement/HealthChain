from healthchain.ai_integrations.baseintegration import AIIntegrationBase
import openai


class OpenAIIntegration(AIIntegrationBase):
    def __init__(self, model_name: str, api_key: str, **params):
        self.api_key = api_key
        self.params = params
        super().__init__(model_name)

    def load_model(self, model_name: str):
        openai.api_key = self.api_key
        return model_name

    def preprocess(self, data):
        return data

    def predict(self, data):
        responses = []
        if isinstance(data, list):
            for item in data:
                response = openai.Completion.create(
                    model=self.model_name, prompt=item, **self.params
                )
                responses.append(response.choices[0].text.strip())
        else:
            response = openai.Completion.create(
                model=self.model_name, prompt=data, max_tokens=50
            )
            responses.append(response.choices[0].text.strip())
        return responses

    def postprocess(self, prediction):
        # For simplicity, return the raw prediction
        return prediction
