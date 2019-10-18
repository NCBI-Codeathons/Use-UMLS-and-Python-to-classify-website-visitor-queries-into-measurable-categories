from werkzeug.utils import secure_filename
from flask import (Flask, flash, request, redirect, url_for, render_template,
                   send_from_directory, send_file, make_response)
import subprocess
import datetime
import os
from flask import Flask
from flask import request
import tempfile
import uuid
import pandas as pd
import matplotlib.pyplot as plt


JOB_INPUT_DIR = os.environ['JOB_INPUT_DIR']
JOB_OUTPUT_DIR = os.environ['JOB_OUTPUT_DIR']
UMLS_SEMANTIC_TYPES_CSV = os.environ['UMLS_SEMANTIC_TYPES_CSV']
STATIC_CONTENT_DIR = os.environ['STATIC_CONTENT_DIR']
TEMPLATE_DIR = os.environ['TEMPLATE_DIR']

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='',
            static_folder=STATIC_CONTENT_DIR,
            template_folder=TEMPLATE_DIR)

app.secret_key = b'e10b5bafe7c27293090b53b95126b839'


# @app.route('/<path:path>')
# def send_static(path):
#     print("Serving static")
#     return send_from_directory('umls-classifier/build', path)


@app.route('/', methods=['GET'])
def index():
    return render_template("index.html")


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

    return render_template("check.html", job_id=job_id)


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

    return render_template("result.html", job_id=job_id)


@app.route('/img/<job_id>', methods=['GET'])
def img(job_id):
    rec_count = 0  # number of records read
    terms_count = 0  # number of UMLS terms found in the records
    # ST_string = ""
    data_df = pd.DataFrame(columns=['query', 'UMLS_ST'])
    input_file = os.path.join(JOB_OUTPUT_DIR, job_id)
    with open(input_file) as fp:
        for line in fp:
            rec_count += 1
            elems = line.rstrip().split('|')
            if len(elems) < 7:
                continue
            query = elems[6]
            ST_string = elems[5]
            ST_string = ST_string.replace("[", "")
            ST_string = ST_string.replace("]", "")
            ST_list = ST_string.split(",")
            for elem in ST_list:
                terms_count += 1
                data_df.loc[len(data_df)] = [query, elem]
    print('Records read: {}'.format(rec_count))
    print('Terms found: {}'.format(terms_count))

    data_basename = os.path.join(JOB_OUTPUT_DIR, job_id + '-')
    # Semantic types counts
    SToutput_file = data_basename + 'semantic_type_counts_output.txt'
    # Semantic groups counts
    SGoutput_file = data_basename + 'semantic_group_counts_output.txt'

    # Bar chart with all Semantic Types counts (ST abbreviations)
    STchart_abbr_file = data_basename + 'UMLS_SemType_abbr_Counts.png'
    # Bar chart with Top 'N' Semantic Types counts (ST abbreviations)
    STchart_TopN_abbr_file = data_basename + 'UMLS_SemType_TopN_abbr_Counts.png'
    # Bar chart with all Semantic Types counts (full ST names)
    STchart_file = data_basename + 'UMLS_SemType_Counts.png'
    # Bar chart with Top 'N' Semantic Types counts (full ST names)
    STchart_TopN_file = data_basename + 'UMLS_SemType_TopN_Counts.png'
    # Bar chart of all semantig group counts
    SGchart_file = data_basename + 'UMLS_SemGroup_counts.png'

    data_df.head()

    summary = data_df.groupby('UMLS_ST').count()

    summary.rename(columns={"query": "count"}, inplace=True)

    sum_sorted = summary.sort_values('count', ascending=False)

    sum_sorted.iloc[:10]

    plt.style.use('ggplot')

    lookup_table = UMLS_SEMANTIC_TYPES_CSV

    mycolumns = ['index', 'TUI', 'abbr', 'name']
    maptable_df = pd.read_csv(lookup_table, index_col=0, names=mycolumns)

    for index, row in sum_sorted.iterrows():
        # print(index, row[0])
        sum_sorted.loc[index, 'name'] = maptable_df.loc[index, 'name']

    top_n = 16   # change this to the number you need

    fig, ax = plt.subplots(figsize=(7, 12))
    sum_sorted.iloc[:top_n].plot(
        kind='barh', x='name', y='count', legend=False, ax=ax)
    ax.set_xlabel('Count')
    ax.set_ylabel('UMLS Semantic Type')
    ax.invert_yaxis()
    ax.set(title='UMLS Semantic Types represented in search queries\n')

    print("Saving chart to {}".format(STchart_file))
    fig.savefig(STchart_file, bbox_inches='tight')

    return send_file(STchart_file, mimetype='image/png')


if __name__ == '__main__':
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    # sess.init_app(app)
    app.debug = True
    app.run()
