#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
import yaml
import re


def convert_implementation_to_psf_type(implementation):
    """Convert Radarr implementation types to PSF condition types"""
    mapping = {
        'LanguageSpecification': 'language',
        'ReleaseTitleSpecification': 'release_title',
        'ReleaseGroupSpecification': 'release_group',
        'EditionSpecification': 'edition',
        'QualityModifierSpecification': 'quality_modifier',
        'SourceSpecification': 'source',
        'ResolutionSpecification': 'resolution',
        'SizeSpecification': 'size',
        'IndexerFlagSpecification': 'indexer_flag'
    }
    return mapping.get(implementation, 'unknown')


def convert_language_value(value):
    """Convert language ID to language code or name"""
    # Common language mappings - extend as needed
    language_map = {
        -2: 'original',
        1: 'english',
        2: 'french', 
        3: 'spanish',
        4: 'german',
        5: 'italian',
        6: 'danish',
        7: 'dutch',
        8: 'japanese',
        9: 'icelandic',
        10: 'chinese',
        11: 'russian',
        12: 'polish',
        13: 'vietnamese',
        14: 'swedish',
        15: 'norwegian',
        16: 'finnish',
        17: 'turkish',
        18: 'portuguese',
        19: 'flemish',
        20: 'greek',
        21: 'korean',
        22: 'hungarian',
        23: 'hebrew',
        24: 'lithuanian',
        25: 'czech',
        26: 'hindi',
        27: 'ukrainian',
        28: 'arabic',
        29: 'bulgarian',
        30: 'brazilian',
        31: 'catalan'
    }
    return language_map.get(value, value)


def convert_specification_to_condition(spec):
    """Convert a Radarr specification to PSF condition format"""
    condition = {
        'name': spec['name'],
        'negate': spec['negate'],
        'required': spec['required'],
        'type': convert_implementation_to_psf_type(spec['implementation'])
    }
    
    fields = spec.get('fields', {})
    implementation = spec['implementation']
    
    if implementation == 'LanguageSpecification':
        condition['language'] = convert_language_value(fields.get('value'))
        if fields.get('exceptLanguage'):
            condition['except_language'] = True
            
    elif implementation in ['ReleaseTitleSpecification', 'ReleaseGroupSpecification', 'EditionSpecification']:
        condition['pattern'] = fields.get('value', '')
        
    elif implementation == 'QualityModifierSpecification':
        condition['modifier'] = fields.get('value')
        
    elif implementation == 'SourceSpecification':
        condition['source'] = fields.get('value')
        
    elif implementation == 'ResolutionSpecification':
        condition['resolution'] = fields.get('value')
        
    elif implementation == 'SizeSpecification':
        condition['min'] = fields.get('min')
        condition['max'] = fields.get('max')
        
    elif implementation == 'IndexerFlagSpecification':
        condition['flag'] = fields.get('value')
    
    return condition


def sanitize_filename(name):
    """Sanitize filename by removing/replacing invalid characters"""
    # Remove or replace characters that are problematic in filenames
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove multiple underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores and spaces
    sanitized = sanitized.strip('_ ')
    return sanitized


def convert_json_to_psf_yaml(json_file, output_dir, dry_run=False):
    """Convert TRaSH Guide JSON Custom Format to PSF YAML format"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            cf_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found: {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON file {json_file}: {e}")
        return False
    
    # Convert specifications to PSF conditions
    conditions = []
    for spec in cf_data.get('specifications', []):
        condition = convert_specification_to_condition(spec)
        conditions.append(condition)
    
    # Create PSF YAML structure
    psf_format = {
        'name': cf_data.get('name', 'Unknown'),
        'conditions': conditions,
        'tests': []  # Empty tests array as per PSF format
    }
    
    # Add optional fields if they exist
    if 'includeCustomFormatWhenRenaming' in cf_data:
        psf_format['includeCustomFormatWhenRenaming'] = cf_data['includeCustomFormatWhenRenaming']
    
    # Create output filename
    filename = sanitize_filename(cf_data.get('name', 'unknown'))
    output_path = output_dir / f"{filename}.yml"
    
    print(f"{'Would convert' if dry_run else 'Converting'} {json_file.name} -> {output_path.name}")
    
    if dry_run:
        print("Preview of YAML output:")
        print("---")
        print(yaml.dump(psf_format, sort_keys=False, default_flow_style=False, indent=2))
        print("---\n")
    else:
        # Create output directory if it doesn't exist
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Write YAML file
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(psf_format, f, sort_keys=False, default_flow_style=False, indent=2, allow_unicode=True)
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Convert TRaSH Guide JSON Custom Formats to PSF YAML format'
    )
    parser.add_argument(
        'input_path',
        help='Input JSON file or directory containing JSON files'
    )
    parser.add_argument(
        '--output-dir',
        default='custom_formats',
        help='Output directory for YAML files (default: custom_formats)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without creating files'
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)
    
    if not input_path.exists():
        print(f"Error: Input path does not exist: {input_path}")
        sys.exit(1)
    
    success_count = 0
    total_count = 0
    
    # Process single file or directory
    if input_path.is_file():
        if input_path.suffix.lower() == '.json':
            total_count = 1
            if convert_json_to_psf_yaml(input_path, output_dir, args.dry_run):
                success_count = 1
        else:
            print(f"Error: Input file must be a JSON file: {input_path}")
            sys.exit(1)
    else:
        # Process directory
        json_files = list(input_path.glob('*.json'))
        if not json_files:
            print(f"Error: No JSON files found in directory: {input_path}")
            sys.exit(1)
        
        total_count = len(json_files)
        print(f"Found {total_count} JSON files to process\n")
        
        if args.dry_run:
            print("DRY RUN - No files will be created\n")
        
        for json_file in sorted(json_files):
            if convert_json_to_psf_yaml(json_file, output_dir, args.dry_run):
                success_count += 1
    
    print(f"\nConversion complete: {success_count}/{total_count} files processed successfully")
    
    if not args.dry_run and success_count > 0:
        print(f"Output files saved to: {output_dir.resolve()}")


if __name__ == "__main__":
    main()