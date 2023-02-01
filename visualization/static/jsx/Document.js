import React, {Component} from 'react';

function Paragraph(props) {
    let metadata = [];
    if (props.meta) {
        metadata = Object.values(Object.assign({}, ...function _flatten(o) {
            return [].concat(...Object.keys(o).map(k =>
                typeof o[k] === 'object' ? _flatten(o[k]) : ({[k]: o[k]})
            ));
        } (props.meta)));
    }
    let content;
    switch (props.ntype) {
        case 'article-title':
            content = <h3 dangerouslySetInnerHTML={{__html: props.content}} />
            break;
        case 'abstract':
            // Fall through
        case 'title':
            content = <h4 dangerouslySetInnerHTML={{__html: props.content}} />
            break;
        default:
            content = <span className="d-block" dangerouslySetInnerHTML={{__html: props.content}} />
    }
    return (
        <li
            id={props.ix}
            className="list-group-item p-2"
            onMouseOver={props.handleMouseOver}
            onMouseOut={props.handleMouseOut}>
            {content}
            <span className="badge badge-pill text-bg-primary mw-100 me-1">{props.ntype}</span>
            {metadata.map((value, key) =>
                <span key={key} className="badge badge-pill text-bg-secondary mw-100 me-1">{value}</span>
            )}
        </li>
    );
}

class Document extends Component {
    parseURL(url) {
        return new URL(url).hostname;
    }
    render() {
        if (!this.props.serialized
            || !this.props.serialized.nodes
            || !this.props.serialized.edges
            || !this.props.serialized.meta) {
            return null;
        }
        return (
            <React.Fragment>
                <div className="row">
                    <div className="col">
                        <div className="card bg-light border-primary shadow-sm mb-3">
                            <div className="card-body">
                                <h3 className="card-title display-6">{this.props.serialized.meta.title}</h3>
                                {this.props.serialized.meta.version &&
                                    <h4 className="card-subtitle mb-2">
                                        {`Version ${this.props.serialized.meta.version}`}
                                    </h4>
                                }
                                {this.props.serialized.meta.url &&
                                    <a
                                        href={this.props.serialized.meta.url}
                                        target="_blank"
                                        className="btn btn-outline-primary d-inline-flex align-items-center">
                                        <span className="me-1">
                                            Open on {this.parseURL(this.props.serialized.meta.url)}
                                        </span>
                                        <svg width="1em" height="1em" viewBox="0 0 16 16" className="bi bi-box-arrow-up-right" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                                            <path fillRule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5z" />
                                            <path fillRule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0v-5z" />
                                        </svg>
                                    </a>
                                }
                            </div>
                        </div>
                    </div>
                </div>
                <div className="row">
                    <div className="col">
                        <div className="card shadow-sm mb-3">
                            <div className={`card-body px-2${this.props.scroll ? " vh-100" : ""}`}>
                                <ul
                                    className={`list-group list-group-flush${this.props.scroll ? " h-100" : ""}`}
                                    style={{overflow: this.props.scroll ? "scroll" : "visible"}}>
                                    {this.props.prepareNodes(this.props.serialized).map(node =>
                                        <Paragraph
                                            key={node.ix}
                                            ix={node.ix}
                                            onMouseOver={this.props.handleMouseOver}
                                            onMouseOut={this.props.handleMouseOut}
                                            content={node.content}
                                            ntype={node.ntype}
                                            meta={node.meta} />
                                    )}
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
            </React.Fragment>
        );
    }
}

export default Document;
