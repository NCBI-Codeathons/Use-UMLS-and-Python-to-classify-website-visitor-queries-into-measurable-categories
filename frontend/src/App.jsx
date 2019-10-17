import React from "react";
// import logo from "./logo.svg";
import "./App.css";

import { Upload, Icon, message, Form } from "antd";

const { Dragger } = Upload;

const props = {
  name: "file",
  multiple: true,
  action: "/upload",
  onChange(info) {
    const { status } = info.file;
    if (status !== "uploading") {
      console.log(info.file, info.fileList);
    }
    if (status === "done") {
      message.success(`${info.file.name} file uploaded successfully.`);
    } else if (status === "error") {
      message.error(`${info.file.name} file upload failed.`);
    }
  }
};

function App() {
  // <img src={logo} className="App-logo" alt="logo" />

  return (
    <div className="App">
      <header className="App-header">
        <Form>
          <Form.Item>
            <Dragger {...props}>
              <p className="ant-upload-drag-icon">
                <Icon type="inbox" />
              </p>
              <p className="ant-upload-text">
                Click here to upload a log file or drag it to this area to
                upload
              </p>
              <p className="ant-upload-hint">
                The log file must be collected from Google Analytics and must be
                in CSV format.
              </p>
            </Dragger>
          </Form.Item>
        </Form>
      </header>
    </div>
  );
}

export default App;
