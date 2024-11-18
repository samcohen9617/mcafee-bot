from function.lambda_function import lambda_handler

event = {
    "testing_flag": True
}

lambda_handler(event, None)