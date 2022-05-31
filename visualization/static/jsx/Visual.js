import React, {Component} from 'react';
import * as d3 from 'd3';
import Document from './Document';
import Form from './Form';

export function getRoot(nodesByIx, nextEdges) {
    // Naive pick first root in array
    let tgt_ix = nextEdges.map(e => e.tgt_ix);
    for (let n of Object.keys(nodesByIx)) {
        if (!tgt_ix.includes(n)) {
            return n;
        }
    }
}

class Visual extends Component {
    constructor(props) {
        super(props);
        this.state = {
            serialized: null,
            etype: []
        };
        this.handleChange = this.handleChange.bind(this);
        this.handleMouseOver = this.handleMouseOver.bind(this);
        this.handleMouseOut = this.handleMouseOut.bind(this);
        this.prepareNodes = this.prepareNodes.bind(this);
        this.svgRef = React.createRef();
    }
    handleChange(key, value) {
        this.setState({
           [key]: value
        });
    }
    componentDidUpdate(prevProps, prevState) {
        if (JSON.stringify(this.state.serialized) !== JSON.stringify(prevState.serialized)) {
            document.title = `${this.state.serialized.meta.title} - ${document.title.split('-').pop().trim()}`;
        }
    }
    handleMouse(target, radius) {
        let circle = d3.select(this.svgRef.current)
            .select(`#n_${target.id}`)
            .select('circle')
            .transition()
            .duration(300)
            .attr('r', radius);
    }
    handleMouseOver(e) {
        this.handleMouse(e.target, 12);
    }
    handleMouseOut(e) {
        this.handleMouse(e.target, 8);
    }
    preprocess(nodes, nodesByIx, currentIx) {
        let node = nodesByIx[currentIx];
        node.content = node.content.replace(/\n/g, '<br />');
        nodes.push(node);
    }
    prepareNodes(graph) {
        let nodes = []
        let nodesByIx = Object.assign({}, ...graph.nodes.map((n) => ({[n.ix]: n})));
        let nextEdges = graph.edges.filter(e => e.etype == 'next');
        let nextEdgesBySrcIx = Object.assign({}, ...nextEdges.map((e) => ({[e.src_ix]: e})));
        let currentIx = getRoot(nodesByIx, nextEdges);
        while (currentIx in nextEdgesBySrcIx) {
            this.preprocess(nodes, nodesByIx, currentIx);
            currentIx = nextEdgesBySrcIx[currentIx].tgt_ix;
        }
        this.preprocess(nodes, nodesByIx, currentIx);
        return nodes;
    }
    render() {
        return (
            <div className="row justify-content-center">
                <div className={`col-5${this.state.serialized ? "" : " d-none"}`}>
                    <Document
                        serialized={this.state.serialized}
                        scroll={true}
                        prepareNodes={this.prepareNodes}
                        handleMouseOver={this.handleMouseOver}
                        handleMouseOut={this.handleMouseOut} />
                </div>
                <div className={`col${this.state.serialized ? "-7" : ""}`}>
                    <div className="row justify-content-center">
                        <div className={`col${this.state.serialized ? "-6" : ""}`}>
                            <Form handleChange={this.handleChange} />
                        </div>
                        <div className={`col-6${this.state.serialized ? "" : " d-none"}`}>
                            <Settings
                                svgRef={this.svgRef}
                                serialized={this.state.serialized}
                                etype={this.state.etype}
                                handleChange={this.handleChange} />
                        </div>
                    </div>
                    {this.state.serialized &&
                        <div className="row jusify-content-center">
                            <div className="col">
                                <Graph
                                    svgRef={this.svgRef}
                                    serialized={this.state.serialized}
                                    etype={this.state.etype} />
                            </div>
                        </div>
                    }
                </div>
            </div>
        );
    }
}

function Checkbox(props) {
    return (
        <div className="custom-control custom-checkbox custom-control-inline">
            <input
                type="checkbox"
                className="custom-control-input"
                id={props.value}
                name={props.value}
                onChange={props.handleChange}
                checked={props.checked} />
            <label className="custom-control-label" htmlFor={props.value}>
                {props.value}
            </label>
        </div>
    );
}

class Settings extends Component {
    constructor(props) {
        super(props);
        this.handleChange = this.handleChange.bind(this);
        this.saveSVG = this.saveSVG.bind(this);
        this.saveButtonRef = React.createRef();
    }
    componentDidUpdate(prevProps) {
        // Keeps checkbox state between multiple consecutive visualizations
        if (prevProps.serialized == null && this.props.serialized) {
            this.props.handleChange('etype', this.parseEdgeTypes(this.props.serialized));
        }
    }
    handleChange(e) {
        // Deep copy to modify props reference
        let etype = JSON.parse(JSON.stringify(this.props.etype));
        if (e.target.checked && !etype.includes(e.target.name)) {
            etype.push(e.target.name);
        } else {
            etype.splice(etype.indexOf(e.target.name), 1);
        }
        this.props.handleChange('etype', etype);
    }
    parseEdgeTypes(serialized) {
        let edges = serialized.edges.concat(serialized.span_edges);
        return Array.from(new Set(edges.map(e => e.etype))).sort();
    }
    saveSVG() {
        let serializer = new XMLSerializer();
        let svg = serializer.serializeToString(this.props.svgRef.current);
        if (!svg.match(/^<svg[^>]+xmlns="http:\/\/www\.w3\.org\/2000\/svg"/)) {
            svg = svg.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
        }
        if (!svg.match(/^<svg[^>]+"http:\/\/www\.w3\.org\/1999\/xlink"/)) {
            svg = svg.replace(/^<svg/, '<svg xmlns:xlink="http://www.w3.org/1999/xlink"');
        }
        svg = `<?xml version="1.0" standalone="no"?>\n${svg}`;
        let blob = new Blob([svg], {type: 'image/svg+xml;charset=utf-8'});
        this.saveButtonRef.current.href = URL.createObjectURL(blob);
        this.saveButtonRef.current.download = `InterText Graph ${new Date().toLocaleString().replaceAll(/[\\/:]/g, '-')}.svg`
        this.saveButtonRef.current.click();
    }
    render() {
        if (!this.props.serialized) {
            return null;
        }
        return (
            <React.Fragment>
                <div className="card bg-light shadow-sm mb-3">
                    <div className="card-body">
                        <h5 className="card-title">Settings</h5>
                        <p className="card-text">Select which edges are shown.</p>
                        <form className="mb-3">
                            {this.parseEdgeTypes(this.props.serialized).map(etype =>
                                <Checkbox
                                    key={etype}
                                    value={etype}
                                    handleChange={this.handleChange}
                                    checked={this.props.etype.includes(etype)} />
                            )}
                        </form>
                        <a
                        ref={this.saveButtonRef}
                        onClick={this.saveSVG}
                        className="btn btn-outline-primary">
                            {"Save SVG "}
                            <svg width="1em" height="1em" viewBox="0 0 16 16" className="bi bi-download" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                                <path fillRule="evenodd" d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z" />
                                <path fillRule="evenodd" d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z" />
                            </svg>
                        </a>
                    </div>
                </div>
            </React.Fragment>
        );
    }
}

class Graph extends Component {
    constructor(props) {
        super(props);
        this.width = 1000;
        this.height = 1000;
    }
    componentDidMount() {
        this.createForceLayoutGraph(this.props.serialized);
    }
    componentDidUpdate(prevProps) {
        if (JSON.stringify(this.props.serialized) !== JSON.stringify(prevProps.serialized)
            || JSON.stringify(this.props.etype) !== JSON.stringify(prevProps.etype)) {
            this.createForceLayoutGraph(this.props.serialized);
        }
    }
    createForceLayoutGraph(serialized) {
        let nodes = serialized.nodes.concat(serialized.span_nodes);
        let edges = serialized.edges.concat(serialized.span_edges);
        // Filter edges based on current selection
        edges = edges.filter(e => this.props.etype.includes(e.etype));
        d3.select(this.props.svgRef.current).selectAll('*').remove();
        edges.map(e => {
            e.source = e.src_ix;
            e.target = e.tgt_ix;
        });
        // Colors from TU Darmstadt Corporate Design
        // https://www.intern.tu-darmstadt.de/arbeitsmittel/corporate_design_vorlagen/index.de.jsp
        // Orange and red for article-title (7c), abstract (8c), title (9c), and parent (7c)
        // Blue for p (1c), list (2c), and next (1c)
        // Green and yellow for label (3c), fig (4c), table-wrap (5c), and boxed-text (6c)
        // Violet for ref (11c)
        // Other violet for span (10c)
        let color = d3.scaleOrdinal()
            .domain(['p', 'list', 'next', 'label', 'fig', 'table-wrap', 'boxed-text', 'ref', 'article-title', 'abstract', 'title', 'parent', 'span'])
            .range(['#004E8A', '#00689D', '#004E8A', '#008877', '#7FAB16', '#B1BD00', '#D7AC00', '#611C73', '#D28700', '#CC4C03', '#B90F22', '#D28700', '#951169']);
        let simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(edges).id(e => e.ix))
            .force('charge', d3.forceManyBody().strength(-140))
            .force('x', d3.forceX([this.width / 2]))
            .force('y', d3.forceY([this.height / 2]));
        d3.select(this.props.svgRef.current)
            .append('defs')
            .append('marker')
            .attr('id', 'arrowhead')
            .attr('viewBox', '0 -5 10 10')
            .attr('refX', 20)
            .attr('refY', 0)
            .attr('markerWidth', 6)
            .attr('markerHeight', 6)
            .attr('orient', 'auto')
            .append('path')
            .attr('d', 'M 0, -5 L 10, 0 L 0, 5');
        let edge = d3.select(this.props.svgRef.current)
            .selectAll('.link')
            .data(edges, e => `${e.source}-${e.target}`)
            .enter()
            .append('line')
            .attr('class', 'link')
            .attr('marker-end', 'url(#arrowhead)')
            .style('stroke', e => color(e.etype))
            .style('stroke-width', '1.5px')
            .style('opacity', .6)
            .style('cursor', 'pointer');
        edge.append('title')
            .text(e => {
                if ('label' in e) {
                    return JSON.stringify({
                        'etype': e.etype,
                        'label': e.label
                    }, null, '\t');
                } else {
                    return e.etype;
                }
            });
        let node = d3.select(this.props.svgRef.current)
            .selectAll('.node')
            .data(nodes, n => n.ix)
            .enter()
            .append('g')
            .attr('id', n => `n_${n.ix}`)
            .attr('class', 'node')
            .on('click', function () {
                let node = d3.select(this);
                let element = document.getElementById(node.data()[0].ix);
                Array.prototype.forEach.call(document.getElementsByClassName('list-group-item active'), x => x.classList.remove('active'));
                element.classList.add('active');
                element.parentElement.scrollTop = element.offsetTop - element.parentNode.offsetTop - 25;
            });
        node.append('circle')
            .attr('r', 8)
            .attr('fill', n => color(n.ntype))
            .style('stroke', '#fff')
            .style('stroke-width', '1.5px')
            .style('cursor', 'pointer');
        node.append('title')
            .text(n => {
                if ('start' in n && 'end' in n && 'label' in n) {
                    return JSON.stringify({
                        'start': n.start,
                        'end': n.end,
                        'label': n.label,
                        'content': n.content
                    }, null, '\t');
                } else {
                    return n.content;
                }
            });
        simulation.on('tick', () => {
            edge.attr('x1', e => e.source.x)
                .attr('y1', e => e.source.y)
                .attr('x2', e => e.target.x)
                .attr('y2', e => e.target.y);
            node.attr('transform', n => `translate(${n.x}, ${n.y})`);
        });
    }
    render() {
        if (!this.props.serialized) {
            return null;
        }
        return (
            <div className="d-inline-block position-relative w-100" style={{paddingBottom: "100%", height: 0}}>
                <svg
                    ref={this.props.svgRef}
                    preserveAspectRatio="xMinYMin meet"
                    viewBox={`0 0 ${this.width} ${this.height}`}
                    className="d-inline-block position-absolute"
                    style={{left: 0}} />
            </div>
        );
    }
}

export default Visual;
