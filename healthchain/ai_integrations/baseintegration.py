from typing import Optional


class AIIntegrationBase:
    def __init__(self, model_name: str, api_key: Optional[str]):
        self.model_name = model_name
        self.model = self.load_model(model_name)

    def load_model(self, model_name: str, api_key: Optional[str]):
        raise NotImplementedError("Subclasses should implement this method.")

    def preprocess(self, data):
        raise NotImplementedError("Subclasses should implement this method.")

    def predict(self, data):
        raise NotImplementedError("Subclasses should implement this method.")

    def postprocess(self, prediction):
        raise NotImplementedError("Subclasses should implement this method.")

    def run(self, data):
        preprocessed_data = self.preprocess(data)
        prediction = self.predict(preprocessed_data)
        return self.postprocess(prediction)
