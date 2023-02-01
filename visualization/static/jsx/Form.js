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
            <div className="card bg-light border-primary shadow-sm h-100 mb-3">
                <div className="card-body">
                    <form encType="multipart/form-data">
                        <h5 className="card-title">Upload</h5>
                        <p className="card-text">Drop or select a serialized InterText Graph.</p>
                        <div className="form-group col-12">
                            {this.state.error &&
                                <div className="alert alert-warning" role="alert">
                                    Error: {this.state.error}
                                </div>
                            }
                            <input
                                type="file"
                                name="graph"
                                className="form-control"
                                accept=".json"
                                onChange={this.handleChange} />
                            <small className="form-text text-muted"><code>.json</code></small>
                        </div>
                    </form>
                </div>
            </div>
        );
    }
}

export default Form;
