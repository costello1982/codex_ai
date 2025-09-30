# Cisco VXLAN EVPN Fabric Terraform Generator

This repository contains a small Python utility that converts a JSON
fabric description into a Terraform project. The generated Terraform
configuration uses the `local` and `null` providers to build baseline
NX-OS configuration snippets for spines, leafs, and VPC-based border
leaf pairs in a Cisco VXLAN EVPN fabric.

## Contents

- `src/generate_terraform.py` – generator script.
- `samples/fabric.template.json` – starter JSON fabric description with two
  spines, eight leafs, and one border leaf pair.

## Quick start

1. **Create or update the fabric JSON file.** Start from
   `samples/fabric.template.json` and adjust the switch names, IP
   addresses, and optional VPC IDs. You can add or remove spines, leafs,
   and border leaf pairs as needed.

2. **Generate the Terraform project.**

   ```bash
   python src/generate_terraform.py samples/fabric.template.json --output terraform_fabric
   ```

   The script creates `main.tf` and reusable Terraform modules under the
   specified output directory.

3. **Review and apply the Terraform configuration.**

   ```bash
   cd terraform_fabric
   terraform init
   terraform apply
   ```

   Terraform produces NX-OS configuration snippets for each switch in the
   `generated/` directory. The files can be used as a baseline for further
   automation or as templates for configuration deployment tools.

## JSON schema overview

| Key             | Description                                                                                  |
|-----------------|----------------------------------------------------------------------------------------------|
| `fabric_name`   | Optional fabric label used for reference only.                                               |
| `spines`        | List of spine switches (`name`, `management_ip`).                                            |
| `leafs`         | List of leaf switches (`name`, `management_ip`).                                             |
| `border_leafs`  | List of border leaf pairs. Each pair includes an optional `pair_name`, optional `vpc_id`,
|                 | and a `members` array with individual switch objects (`name`, `management_ip`).              |

## Example topology

```
                     +---------------------+
                     |     Spine-1         |
                     +---------------------+
                        /    /    |    \ \
                       /    /     |     \ \
                      /    /      |      \ \
                     v    v       v       v  
+--------------+ +--------------+ +--------------+ +--------------+
|   Leaf-1     | |   Leaf-2     | |   Leaf-3     | |   Leaf-4     |
+--------------+ +--------------+ +--------------+ +--------------+
                     ^    ^       ^       ^
                     |    |       |       |
                     |    |       |       |
                     |    |       |       |
+--------------+ +--------------+ +--------------+ +--------------+
|   Leaf-5     | |   Leaf-6     | |   Leaf-7     | |   Leaf-8     |
+--------------+ +--------------+ +--------------+ +--------------+
                      \\       |       |       //
                       \\      |      //
                        \\     |     //
                     +---------------------+
                     |     Spine-2         |
                     +---------------------+

                +-------------------+     +-------------------+
                |  Border-1A (VPC)  |-----|  Border-1B (VPC)  |
                +-------------------+     +-------------------+
```

The ASCII diagram represents the default template with two spines,
eight leaf switches, and a single VPC-enabled border leaf pair.

## Notes

- The generated Terraform relies on the `hashicorp/local` and
  `hashicorp/null` providers; Terraform will download them automatically
  during `terraform init`.
- The configuration snippets are basic and should be extended or refined
  to match the requirements of the target environment.
- For environments where Terraform is not desired, the JSON model can be
  consumed by other automation frameworks (such as Ansible) by adapting
  the generator script.
