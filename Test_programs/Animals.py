from speaker import Speaker
class Animal:
    def eat(self):
        print("It eats.")
    def sleep(self):
        print("It sleeps.")

class Bird(Animal):
    """
    A class to represent a bird, which is a type of animal.

    Methods
    -------
    fly():
        Prints a message indicating that the bird can fly.
    sing():
        Prints a message indicating that the bird can sing.
    speak(text="No sound is found."):
        Prints a message indicating that the bird cannot speak but can write the provided text.
        Parameters:
            text (str): The text to be printed. Default is "No sound is found."
    """
    def fly(self):
        print("It flies in the sky.")
    def sing(self):
        print("It sings.")
    def speak(self, text = "No sound is found."):
        print("It can not speak but can write it.")
        print(text)
        
class SingingBird(Speaker, Bird):
    def __init__(self, birdName = "Bird Name"):
        self.birdName = birdName
    def printBirdName(self):
        print("This is a {birdName}!".format(birdName = self.birdName))

print(SingingBird.__bases__)

duck = SingingBird("Duck")
duck.printBirdName()
duck.eat()
duck.sleep()
duck.fly()
duck.sing()
duck.speak("Quack quack, quack quack, quack quack")