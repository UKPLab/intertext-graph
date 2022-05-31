import React, {Component} from 'react';

class Form extends Component {
    constructor(props) {
        super(props);
        this.state = {
            label: "Choose File",
            error: null
        };
        this.handleChange = this.handleChange.bind(this);
    }
    handleChange(e) {
        let files = e.target.files;
        if (files.length > 0) {
            this.setState({
                label: files[0].name,
            });
            let reader = new FileReader();
            reader.onloadend = () => {
                this.props.handleChange('serialized', JSON.parse(reader.result));
            }
            reader.readAsText(files[0])
        }
    }
    render() {
        return (
            <div className="card bg-light shadow-sm mb-3">
                <div className="card-body">
                    <form encType="multipart/form-data">
                        <h5 className="card-title">Upload</h5>
                        <p className="card-text">Drop or select a serialized InterText Graph.</p>
                        <div className="form-row">
                            <div className="form-group col-12">
                                {this.state.error &&
                                    <div className="alert alert-warning" role="alert">
                                        Error: {this.state.error}
                                    </div>
                                }
                                <div className="custom-file">
                                    <input
                                        type="file"
                                        name="graph"
                                        className="custom-file-input"
                                        accept=".json"
                                        onChange={this.handleChange} />
                                    <small className="form-text text-muted">
                                        <code>.json</code>
                                    </small>
                                    <label className="custom-file-label overflow-hidden">{this.state.label}</label>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        );
    }
}

export default Form;
