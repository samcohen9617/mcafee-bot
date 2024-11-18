from function.lambda_function import lambda_handler

event = {
    "testing_flag": False
}

lambda_handler(event, None)