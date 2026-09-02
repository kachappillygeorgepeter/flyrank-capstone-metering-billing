#Pricing, dont change without updating the test material

# Price per 1k tokens in USD
INPUT_TOKEN_RATE        = 0.003    # $0.003  per 1k — standard input
CACHED_TOKEN_RATE       = 0.0003   # $0.0003 per 1k — cached input
OUTPUT_TOKEN_RATE       = 0.015    # $0.015  per 1k — generated output
REASONING_TOKEN_RATE    = 0.015    # $0.015  per 1k 

# To calculate cost of one request
def calculate_cost(input_tokens: int, cached_tokens: int,
                   output_tokens: int, reasoning_tokens: int) -> float:
    cost = (
        (input_tokens/1000)*INPUT_TOKEN_RATE +
        (cached_tokens/1000)*CACHED_TOKEN_RATE +
        (output_tokens/1000)*OUTPUT_TOKEN_RATE +
        (reasoning_tokens/1000)*REASONING_TOKEN_RATE
    )
    return round(cost, 6)  # Round to 6 decimal places for precision

# To calculate total cost from events
def calculate_total_cost_from_events(events: list) -> float:
    total = 0.0
    for event in events:
        input_t, cached_t, output_t, reasoning_t = event
        total += calculate_cost(input_t, cached_t, output_t, reasoning_t)
    return round(total, 6)