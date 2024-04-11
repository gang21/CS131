from interpreterv3 import Interpreter

def main():
  program_source = """
func main() {
  a = -5;
  print(a == true);
}
"""
  interpreter = Interpreter()
  interpreter.run(program_source)



if __name__ == "__main__":
    main()
