from werkzeug.utils import secure_filename
from flask import (Flask, flash, request, redirect, url_for,
                   send_from_directory, make_response)
import subprocess
import datetime
import os
from flask import Flask
from flask import request
import tempfile
import uuid

JOB_INPUT_DIR = os.environ['JOB_INPUT_DIR']
JOB_OUTPUT_DIR = os.environ['JOB_OUTPUT_DIR']


# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')

app.secret_key = b'e10b5bafe7c27293090b53b95126b839'


@app.route('/<path:path>')
def send_static(path):
    print("Serving static")
    return send_from_directory('umls-classifier/build', path)


@app.route('/', methods=['GET'])
def cgi():
    return '''
    <!doctype html>
    <title>Upload Log File</title>
    <h1>Upload Google Analytics Log File</h1>
    <p>Please upload a Google Analytics log file in CSV format.
    <form
        action="''' + url_for("upload_file") + '''"
        method="post"
        enctype="multipart/form-data">
      <input type="file" name="file">
      <input
        type="submit"
        value="Upload"
        onClick="this.disabled=true; this.value='Processing...';">
    </form>
    '''


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    filename = secure_filename(file.filename)
    job_id = str(uuid.uuid4())
    print("Job ID: {}".format(job_id))
    os.makedirs(JOB_INPUT_DIR, exist_ok=True)
    input_pathname = os.path.join(JOB_INPUT_DIR, job_id)
    print("Input file: {}".format(input_pathname))
    file.save(input_pathname)
    return redirect(url_for('check', job_id=job_id))


@app.route('/check/<job_id>', methods=['GET'])
def check(job_id):
    if os.path.isfile(os.path.join(JOB_OUTPUT_DIR, job_id)):
        return redirect(url_for('done', job_id=job_id))

    return ('''
    <html>
        <head>
            <meta http-equiv="refresh" content="3;url=''' +
                url_for('check', job_id=job_id) + '''" />
        </head>
        <body>
            <h1>Running job {}...</h1>
        </body>
    </html>'''.format(job_id))


@app.route('/done/<job_id>', methods=['GET'])
def done(job_id):
    result = open(os.path.join(JOB_OUTPUT_DIR, job_id)).read()
    lines = result.split('\n')
    error = None
    if len(lines) == 0:
        error = "Job failed. Result is empty"
    elif lines[0].startswith('ERROR MESSAGE'):
        error = lines[0][len('ERROR MESSAGE'):]
        if error.startswith(': '):
            error = error[2:]
        if error.startswith('ERROR: '):
            error = error[len('ERROR: '):]
    if error:
        return "Error: {}".format(error)

    response = make_response(result, 200)
    response.mimetype = "text/plain"
    return response


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    # sess.init_app(app)
    app.debug = False
    app.run()
