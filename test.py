from flask import Flask
test = Flask(__name__)

@test.route('/')
def testing():
  return 'Hello World'

test.run(debug=True)