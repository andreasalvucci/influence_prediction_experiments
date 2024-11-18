import argparse
import os
from rdflib import Graph

def merge_graphs(input_folder, output_file):
    merged_graph = Graph()

    for filename in os.listdir(input_folder):
        if filename.endswith(".ttl") or filename.endswith(".rdf") or filename.endswith(".xml"):
            include = input(f"Do you want to include {filename}? (yes/no): ").strip().lower()
            if include == 'yes':
                file_path = os.path.join(input_folder, filename)
                graph = Graph()
                graph.parse(file_path)
                merged_graph += graph

                # Bind namespaces from the included graph
                for prefix, namespace in graph.namespaces():
                    merged_graph.bind(prefix, namespace)
    create_predicates_file = input("Do you want to create a predicates file? (yes/no): ").strip().lower()
    if create_predicates_file == 'yes':
        predicates_file = output_file.replace('.ttl', '_predicates.csv')
        predicates = set()
        for s, p, o in merged_graph:
            predicates.add(str(p))
        
        with open(predicates_file, 'w') as f:
            f.write(','.join(predicates))
        
        print(f"Predicates file saved to {predicates_file}")
    merged_graph.serialize(destination=output_file, format='turtle')
    print(f"Merged graph saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Merge RDF graphs in a given folder")
    parser.add_argument("input_folder", help="Folder containing RDF graph files")

    args = parser.parse_args()
    output_file = input("Enter the output filename (with .ttl extension): ").strip()
    merge_graphs(args.input_folder, output_file)

if __name__ == "__main__":
    main()
    
    