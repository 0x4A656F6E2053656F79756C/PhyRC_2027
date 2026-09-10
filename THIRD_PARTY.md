# Third-party provenance and redistribution

This repository is a private maintenance snapshot, not a claim that all included
assets have an unrestricted redistribution license. Do not make it public or
redistribute the human/robot/garment inputs until their rights are confirmed.

| Component | Actual use and source | Distribution decision |
|---|---|---|
| NVIDIA Isaac Sim 6.0.1 | Official `nvcr.io/nvidia/isaac-sim` container; base digest pinned in Dockerfile | Download only; NVIDIA terms apply |
| DexGarmentLab | Local, extensively modified 16-file teleop dependency closure; original project: https://github.com/wayrise/DexGarmentLab | Maintain the working modified snapshot under `src/DexGarmentLab`; training/policy code omitted |
| RCareWorld-2.0 Stretch4 | Local `assets/robots/stretch_4/stretch_4.usd`; visual, collision, articulation data are embedded | Only this USD included; no exact public upstream repository/download was established |
| Female mannequin | `female2_c4-c5.usd` and its `textures/c4-c5.jpg`, supplied in `manikin_assets_male_female.zip` | Only these two inputs included; no public URL/license established; possible SMPL-X-derived restrictions require owner review |
| Modelink shirt | Local `N_PR_2000_TShirt001.usd`, mesh `/t_shirt/t_shirt_001/t_shirt_001` | Include raw input, generate modified rest geometry locally; no exact public download established |
| Kitchen floor texture | https://huggingface.co/datasets/wayrise/DexGarmentLab at `2ba4092676006bc98c257e7b822de39526fd9692`, `Scene.zip` | Fetch the single locked JPEG, never commit the archive or texture |
| Python packages | termcolor, scipy, matplotlib; remaining libraries supplied by Isaac Sim | Install pinned additional versions, do not vendor wheels or environments |
| Initial cloth visual material | DexGarmentLab `Assets/Material/Garment/linen_Pumpkin.usd` and its BaseColor/Roughness JPEGs at commit `e4e298e696bae5d866ded3b31e0ae27becea5376` | Download only, lock SHA256, normalize USD metadata in the generated runtime |

The Hugging Face dataset card declares Apache-2.0. That declaration is not
automatically a license grant for unrelated locally supplied USD files. No
repository-wide MIT/Apache license is invented for the combined snapshot.
Upstream DexGarmentLab's current public commit during this audit was
`e4e298e696bae5d866ded3b31e0ae27becea5376`; it is a provenance reference, **not**
a claim that the local snapshot is byte-identical to that revision.

The public `Garment.zip` central directory was checked for the local Modelink
filename/path and did not contain a matching entry. The official asset download
script points to the Hugging Face dataset, not to the private local asset paths.
Robot USD dependency inspection found only bundled `OmniPBR.mdl`; mannequin
dependency inspection found only the included JPEG. No sibling project folder
is needed after preparation.

## Why there are no submodules yet

The currently executed teleop is a locally modified snapshot, not an unmodified
checkout with a recoverable upstream commit. Adding a submodule to today's
upstream HEAD would lose the 6.0.1 FEM port, control fixes and latest geometry.
There is no confirmed public Git repository for this exact Stretch4 USD either.
Submodules should be introduced only for a verified upstream and pinned commit,
with our changes maintained in an explicit fork or patch series. Their absence
here is intentional, not a missing recursive-clone step.
