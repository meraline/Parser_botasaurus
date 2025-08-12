# Parser_botasaurus

VIN parser that retrieves official data from GIBDD and supplemental information from other sources.

## VIN list file

`vin_parser.py` accepts a path to a JSON file containing VIN codes. The file must have the following structure:

```json
{
  "vins": [
    "JMBXTGF2WDZ013380",
    "VF1AAAAAA12345678"
  ]
}
```

A sample file is provided as `sample_vins.json`.

## Usage

Run the parser by passing the path to your JSON file:

```bash
python vin_parser.py sample_vins.json
```

Each VIN in the file will be processed via `parse_by_vin`.

