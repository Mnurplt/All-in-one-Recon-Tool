
from datetime import datetime


def generate_number():
    now = datetime.now()

    x = now.hour + now.minute
    y = 5 * x + 7

    if y > 100:
        y = y % 100

    if y < 1:
        y = 1

    return y


def guessing_game():
    target = generate_number()
    attempts = 0

    print("1 ile 100 arasında bir sayı tahmin et!")

    while True:
        guess = int(input("Tahminin: "))
        attempts += 1

        if guess < target:
            print("Daha büyük!")
        elif guess > target:
            print("Daha küçük!")
        else:
            print(f"Tebrikler! {attempts} denemede buldun.")
            break


guessing_game()
