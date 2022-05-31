# InterText Graph Library

This is the official repository for the _InterText Graph_ library introduced in the paper _"Revise and Resubmit: An Intertextual Model of Text-based Collaboration in Peer Review"_.

Have a look at our preprint: [Kuznetsov et al., 2022](https://arxiv.org/abs/2204.10805).

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
@misc{https://doi.org/10.48550/arxiv.2204.10805,
  doi = {10.48550/ARXIV.2204.10805},
  url = {https://arxiv.org/abs/2204.10805},
  author = {Kuznetsov, Ilia and Buchmann, Jan and Eichler, Max and Gurevych, Iryna},
  keywords = {Computation and Language (cs.CL)},
  title = {Revise and Resubmit: An Intertextual Model of Text-based Collaboration in Peer Review},
  publisher = {arXiv},
  year = {2022},
  copyright = {Creative Commons Attribution Non Commercial Share Alike 4.0 International}
}
```

Contact Persons: Max Eichler, Jan Buchmann, Ilia Kuznetsov

<https://www.ukp.tu-darmstadt.de>

<https://www.tu-darmstadt.de>

This repository contains experimental software and is published for the sole purpose of giving additional background details on the respective publication.
