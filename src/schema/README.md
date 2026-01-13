# Module Schema

Systeme de generation automatique de formulaires Streamlit a partir de definitions de schemas.

## Structure du module

```
src/schema/
├── __init__.py           # Exports publics
├── definitions.py        # Classes de base (WidgetType, FieldSchema, etc.)
├── form_generator.py     # Generateur de formulaires
├── list_generator.py     # Generateur de DataFrames/listes
├── dialog_generator.py   # Generateur de dialogs CRUD
└── schemas/              # Definitions des entites
    ├── operation.py      # Schema Operation
    ├── flotteur.py       # Schema Flotteur
    └── resultat_humain.py # Schema ResultatHumain
```

## Composants principaux

### WidgetType

Types de widgets Streamlit disponibles:

| Type | Description |
|------|-------------|
| `TEXT_INPUT` | Champ texte simple |
| `NUMBER_INPUT` | Champ numerique |
| `SELECTBOX` | Liste deroulante |
| `MULTISELECT` | Selection multiple |
| `DATE_INPUT` | Selecteur de date |
| `TIME_INPUT` | Selecteur d'heure |
| `TEXT_AREA` | Zone de texte |
| `CHECKBOX` | Case a cocher |

### FieldSchema

Definition d'un champ de formulaire:

```python
FieldSchema(
    name="operation_id",        # Nom du champ (correspond au modele SQLAlchemy)
    label="ID Operation",       # Label affiche
    widget=WidgetType.NUMBER_INPUT,
    required=True,
    min_value=1,
    step=1,
    help_text="Identifiant unique",
    section="identification",   # Groupe/section
    order=1,                    # Ordre d'affichage
    visible_in_list=True,       # Afficher dans la liste
    list_order=1,               # Ordre dans la liste
    editable=True,              # Modifiable en edition
)
```

### FormSection

Definition d'une section de formulaire:

```python
FormSection(
    name="identification",
    label="Identification",
    columns=2,           # Nombre de colonnes
    collapsible=False,   # Section repliable
    expanded=True,       # Etat initial si repliable
    order=1,             # Ordre d'affichage
)
```

### EntitySchema

Schema complet d'une entite:

```python
EntitySchema(
    name="operation",
    model_class="Operation",
    crud_instance="crud_operation",
    primary_key="operation_id",
    display_name="Operation",
    display_name_plural="Operations",
    sections=[...],
    fields=[...],
)
```

## Utilisation

### Import

```python
from src.schema import (
    FieldSchema, EntitySchema, WidgetType,
    FormGenerator, ListGenerator, DialogGenerator,
)
from src.schema.schemas import OPERATION_SCHEMA
```

### Generer un formulaire

```python
gen = FormGenerator(OPERATION_SCHEMA)
values = gen.render_form("create_op", current_values=None)
is_valid, errors = gen.validate(values)
cleaned = gen.clean_values(values)
```

### Generer une liste

```python
gen = ListGenerator(OPERATION_SCHEMA)
df = gen.build_dataframe(operations)
selected_id = gen.render_list(operations, on_select=handle_select)
```

### Generer un dialog CRUD

```python
gen = DialogGenerator(OPERATION_SCHEMA)

@st.dialog("Nouvelle operation")
def show_create():
    gen.create_dialog(user="admin")

@st.dialog("Modifier operation")
def show_edit(op_id):
    gen.edit_dialog(op_id, user="admin", can_delete=True)
```

## Ajouter un nouveau champ

1. Ajouter un `FieldSchema` dans la liste `fields` du schema
2. Specifier la section appropriee (ou en creer une nouvelle)
3. Si le champ utilise une liste d'options, ajouter l'`enum_ref` correspondant dans `enums.py`

## Schemas existants

- `OPERATION_SCHEMA` - Operations de sauvetage maritime
- `FLOTTEUR_SCHEMA` - Flotteurs impliques dans une operation
- `RESULTAT_HUMAIN_SCHEMA` - Resultats humains (personnes secourues)
