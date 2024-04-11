from interpreterv4 import Interpreter

def main():
  program_source = """
func main() {
  y = @;
  y.x = 10;
  y.foo = lambda() { this = @; this.y = 10; };
  y.foo();
  print(y.x); 
}
"""
  interpreter = Interpreter()
  interpreter.run(program_source)



if __name__ == "__main__":
    main()
