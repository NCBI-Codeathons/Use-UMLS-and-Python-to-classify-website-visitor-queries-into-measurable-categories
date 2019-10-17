from werkzeug.utils import secure_filename
from flask import Flask, flash, request, redirect, url_for, send_from_directory
import subprocess
import datetime
import os
from flask import Flask
from flask import request
import tempfile
import uuid

METAMAP_CLIENT_JAR = os.environ['METAMAP_CLIENT_JAR']
JOB_OUTPUT_DIR = os.environ['JOB_OUTPUT_DIR']


# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')

app.secret_key = b'secret secret'


@app.route('/<path:path>')
def send_static(path):
    print("Serving static")
    return send_from_directory('umls-classifier/build', path)


def process_umls_job(input_filename, output_filename):
    args = ["java", "-jar", METAMAP_CLIENT_JAR, input_filename]
    print("Running metamap job with arguments: {}".format(args))
    with open(output_filename, 'wb') as output_file:
        subprocess.run(args, shell=False, check=True, stdout=output_file)


@app.route('/', methods=['GET'])
def index():
    return redirect(url_for('cgi'))


@app.route('/cgi', methods=['GET'])
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
    with tempfile.NamedTemporaryFile() as temp:
        filename = secure_filename(file.filename)
        file.save(temp.name)
        job_id = str(uuid.uuid4())
        print("Input file: {}".format(temp.name))
        print("Job ID: {}".format(job_id))
        process_umls_job(temp.name, os.path.join(JOB_OUTPUT_DIR, job_id))
        return redirect(url_for('done', job_id=job_id))


@app.route('/done/<job_id>', methods=['GET'])
def done(job_id):
    result = open(os.path.join(JOB_OUTPUT_DIR, job_id)).readlines()
    if len(result) == 0:
        error = "Job failed. Result is empty"
    elif result[0].startswith('ERROR MESSAGE'):
        error = result[0][len('ERROR MESSAGE'):]
        if error.startswith(': '):
            error = error[2:]
        if error.startswith('ERROR: '):
            error = error[len('ERROR: '):]
    if error:
        return "Error: {}".format(error)
    return '''
	<!doctype html>
	<title>Processing done</title>
	<h1>Job {} has been successfully processed</h1>
	'''.format(job_id)


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    # sess.init_app(app)
    app.debug = False
    app.run()
