# InterText Graph Library

This is the official repository for the _InterText Graph_ library introduced in the paper _"Revise and Resubmit: An Intertextual Model of Text-based Collaboration in Peer Review"_, see the [paper repository](https://github.com/UKPLab/f1000rd) for more details.

## Installation

To install run `pip install git+https://github.com/UKPLab/intertext-graph.git`

When using the sentence splitter install `en_core_sci_sm` manually from [scispaCy](https://allenai.github.io/scispacy/).

## Tutorial

Check the `/tutorial` folder for sample data and notebooks explaining how the _Intertext Graph_ library works.

## Graph Visualization

We provide a small web application to visualize serialized _Intertext Graphs_.

1. Go to `visualization/` and execute `npm install` to compile the visualization web app.
2. Open the `visualization/index.html` file, and get started.

## Citation

Please use the following citation:

```
@article{10.1162/coli_a_00455,
    author = {Kuznetsov, Ilia and Buchmann, Jan and Eichler, Max and Gurevych, Iryna},
    title = "{Revise and Resubmit: An Intertextual Model of Text-based Collaboration in Peer Review}",
    journal = {Computational Linguistics},
    pages = {1-38},
    year = {2022},
    month = {08},
    issn = {0891-2017},
    doi = {10.1162/coli_a_00455},
    url = {https://doi.org/10.1162/coli\_a\_00455},
    eprint = {https://direct.mit.edu/coli/article-pdf/doi/10.1162/coli\_a\_00455/2038043/coli\_a\_00455.pdf},
}
```

Contact Persons: Max Eichler, Jan Buchmann, Ilia Kuznetsov

<https://www.ukp.tu-darmstadt.de>

<https://www.tu-darmstadt.de>

This repository contains experimental software and is published for the sole purpose of giving additional background details on the respective publication.
