import logging


class EHRClientMethod:
    def __init__(self, func, workflow=None, use_case=None):
        self.func = func
        self.workflow = workflow
        self.use_case = use_case

    def __call__(self, *args, **kwargs):
        # Call the function to process data
        data = self.func(*args, **kwargs)

        # Use the strategy (use case) to construct the request with the output from func
        if self.use_case:
            request_data = self.use_case.construct_request(data, self.workflow)
            return request_data 
        else:
            return data

