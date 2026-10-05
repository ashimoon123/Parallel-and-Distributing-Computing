import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gui import GPUOffloadingClient

def main():
    app = GPUOffloadingClient()
    app.mainloop()

if __name__ == "__main__":
    main()
