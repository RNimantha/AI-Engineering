def calculate_average(numbers):
    if not numbers:
        return 0
    numeric = [num for num in numbers if isinstance(num, (int, float))]
    if not numeric:
        return 0
    return sum(numeric) / len(numeric)


def get_user_name(user):
    name = user.get("name") if user else None
    return str(name).upper() if name is not None else ""