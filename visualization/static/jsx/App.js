import React from 'react';
import Visual from './Visual';

function App() {
    return (
        <React.Fragment>
            <div className="jumbotron bg-light border-bottom rounded-0 text-center">
                <div className="container-fluid">
                    <h1 className="font-weight-light">InterText Graph</h1>
                    <p className="lead">Visualize Documents</p>
                </div>
            </div>
            <div className="container-fluid">
                <Visual />
            </div>
        </React.Fragment>
    );
}

export default App;
