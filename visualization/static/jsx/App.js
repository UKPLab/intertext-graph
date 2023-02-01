import React from 'react';
import Visual from './Visual';

function App() {
    return (
        <React.Fragment>
            <div className="container col-md-8 col-xl-6">
                <div className="row text-center">
                    <div className="col-sm mb-3">
                        <div className="mb-4">
                            <a className="text-decoration-none" href="https://intertext.ukp-lab.de">
                                <img src="static/intertext_logo.svg" height="120" alt="InterText" className="d-block mx-auto" />
                            </a>
                        </div>
                        <p className="lead fs-2">Visualize Documents</p>
                    </div>
                </div>
            </div>
            <div className="container-fluid">
                <Visual />
            </div>
        </React.Fragment>
    );
}

export default App;
