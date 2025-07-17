import os
from typing import List, Optional, Tuple, Dict
from jinja2 import Environment, FileSystemLoader, select_autoescape
import re

# Database Schema Definition Classes (as provided previously)
class Column:
    """Represents a database column with all metadata attributes"""
    def __init__(self, name: str):
        self.name = name
        self.data_type: Optional[str] = None
        self.char_length: Optional[int] = None
        self.numeric_precision: Optional[int] = None
        self.numeric_scale: Optional[int] = None
        self.nullable: bool = True
        self.default: Optional[str] = None
        self.is_primary: bool = False
        self.primary_key_position: Optional[int] = None
        self.foreign_key_ref: Optional[Tuple[str, str, str]] = None
        self.constraints: List[Dict] = []

class PrimaryKey:
    """Defines a primary key constraint"""
    def __init__(self, name: Optional[str], columns: List[str]):
        self.name = name
        self.columns = columns

class ForeignKey:
    """Defines a foreign key relationship"""
    def __init__(self, name: Optional[str], columns: List[str],
                 ref_table: str, ref_columns: List[str]):
        self.name = name
        self.columns = columns
        self.ref_table = ref_table
        self.ref_columns = ref_columns

class Constraint:
    """Represents table constraints (CHECK, UNIQUE, etc.)"""
    def __init__(self, name: str, ctype: str,
                 expression: Optional[str] = None,
                 columns: Optional[List[str]] = None):
        self.name = name
        self.ctype = ctype
        self.expression = expression
        self.columns = columns or []

class Index:
    """Database index definition"""
    def __init__(self, name: str, table: str, columns: List[str],
                 is_unique: bool = False, method: Optional[str] = None):
        self.name = name
        self.table = table
        self.columns = columns
        self.is_unique = is_unique
        self.method = method

class Table:
    """Complete table metadata container"""
    def __init__(self, name: str, schema: Optional[str] = None,
                 database: Optional[str] = None, table_type: str = 'TABLE'):
        self.database = database
        self.schema = schema
        self.name = name
        self.table_type = table_type
        self.primary_key = None
        self.columns: Dict[str, Column] = {}
        self.foreign_keys: List[ForeignKey] = []
        self.constraints: List[Constraint] = []
        self.is_view = False
        self.view_definition: Optional[str] = None
        self.is_materialized = False


class CRUDVueGenerator:
    """
    Generates Vue 3 frontend with:
    - PrimeVue components
    - SBAdmin/Material Design layout
    - Complete CRUD interfaces
    - Authentication integration
    - Vitest unit tests
    """

    def __init__(self, tables: List[Table]):
        """
        Args:
            tables: List of Table objects to generate UIs for
        """
        self.tables = tables
        # Set up Jinja2 environment
        current_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(current_dir, "templates", "frontend")
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml', 'vue']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        self._add_jinja_filters()

    def _add_jinja_filters(self):
        """Adds custom filters to the Jinja2 environment."""
        self.env.filters['snake_case'] = self._to_snake_case
        self.env.filters['pascal_case'] = self._to_pascal_case
        self.env.filters['kebab_case'] = self._to_kebab_case
        self.env.filters['singularize'] = self._singularize
        self.env.filters['pluralize'] = self._pluralize
        self.env.filters['sql_to_js_type'] = self._sql_type_to_js_type
        self.env.filters['get_pk_name'] = self._get_pk_name
        self.env.filters['get_pk_type'] = self._get_pk_type
        self.env.filters['get_default_js_value_for_type'] = self._get_default_js_value_for_type


    def _to_snake_case(self, name: str) -> str:
        """Converts PascalCase/CamelCase/Space-separated to snake_case."""
        name = name.replace(' ', '_') # Handle spaces first
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def _to_pascal_case(self, name: str) -> str:
        """Converts snake_case/kebab-case/space-separated to PascalCase."""
        return ''.join(word.capitalize() for word in re.split(r'[-_ ]', name))

    def _to_kebab_case(self, name: str) -> str:
        """Converts PascalCase/snake_case/space-separated to kebab-case."""
        name = name.replace(' ', '-') # Handle spaces first
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower().replace('_', '-')

    def _singularize(self, name: str) -> str:
        """Basic singularization (for schema names)."""
        if name.endswith('s') and not name.endswith('ss'):
            return name[:-1]
        return name

    def _pluralize(self, name: str) -> str:
        """Basic pluralization (for router paths)."""
        if not name.endswith('s'):
            return name + 's'
        return name

    def _sql_type_to_js_type(self, column: Column) -> str:
        """Converts SQL data types to JavaScript types."""
        data_type = column.data_type.lower()
        if data_type in ['varchar', 'text', 'char', 'uuid', 'json', 'jsonb']:
            return 'string'
        elif data_type in ['integer', 'smallint', 'bigint', 'serial', 'bigserial']:
            return 'number'
        elif data_type in ['boolean']:
            return 'boolean'
        elif data_type in ['float', 'double precision', 'real', 'numeric', 'decimal']:
            return 'number'
        elif data_type in ['date', 'timestamp', 'timestamptz', 'datetime']:
            return 'Date' # JavaScript Date object
        elif data_type in ['bytea', 'blob']:
            return 'string' # Often represented as base64 string in JS
        return 'any' # Fallback for unhandled types

    def _get_pk_column(self, table: Table) -> Optional[Column]:
        """Returns the primary key column, assuming a single PK column for simplicity."""
        if table.primary_key and table.primary_key.columns:
            pk_col_name = table.primary_key.columns[0]
            return table.columns.get(pk_col_name)
        return None

    def _get_pk_type(self, table: Table) -> str:
        """Returns the JavaScript type of the primary key."""
        pk_column = self._get_pk_column(table)
        if pk_column:
            return self._sql_type_to_js_type(pk_column)
        return "number" # Default to number if no PK found

    def _get_pk_name(self, table: Table) -> str:
        """Returns the name of the primary key column."""
        pk_column = self._get_pk_column(table)
        if pk_column:
            return pk_column.name
        return "id" # Default to 'id'

    def _get_default_js_value_for_type(self, column: Column):
        """Returns a suitable default JS value for testing based on column type."""
        data_type = column.data_type.lower()
        if data_type in ['varchar', 'text', 'char', 'uuid', 'json', 'jsonb']:
            return f"'{self._to_snake_case(column.name)}_test'"
        elif data_type in ['integer', 'smallint', 'bigint', 'serial', 'bigserial']:
            return 1
        elif data_type in ['boolean']:
            return 'true'
        elif data_type in ['float', 'double precision', 'real', 'numeric', 'decimal']:
            return 1.0
        elif data_type in ['date']:
            return "'2024-01-01'"
        elif data_type in ['timestamp', 'timestamptz', 'datetime']:
            return "'2024-01-01T12:00:00Z'"
        elif data_type in ['bytea', 'blob']:
            return "'test_bytes'"
        return "null"


    def generate(self, output_dir: str = "frontend"):
        """
        Generates complete frontend structure:

        frontend/
        ├── src/
        │   ├── views/           # Page components
        │   │   └── {table}View.vue
        │   ├── components/      # Shared components
        │   ├── router/          # Vue Router config
        │   ├── store/           # Pinia state management
        │   ├── services/        # API clients
        │   ├── tests/           # Vitest unit tests
        │   │   └── {table}.spec.js
        │   ├── App.vue          # Main layout (SBAdmin)
        │   └── main.js          # App entrypoint
        ├── public/              # Static assets
        │   └── index.html       # Main HTML entry point
        └── package.json         # Dependencies

        Uses Jinja2 templates from templates/frontend/
        """
        # Create output directories
        base_path = os.path.join(os.getcwd(), output_dir)
        os.makedirs(base_path, exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "views"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "components"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "router"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "store"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "services"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "src", "tests"), exist_ok=True)
        os.makedirs(os.path.join(base_path, "public"), exist_ok=True) # For static assets

        # Generate per-table files
        for table in self.tables:
            table_snake_case = self._to_snake_case(table.name)
            table_pascal_case = self._to_pascal_case(table.name)
            table_kebab_case = self._to_kebab_case(table.name)
            table_singular_kebab = self._to_kebab_case(self._singularize(table.name))
            table_plural_kebab = self._to_kebab_case(self._pluralize(table.name))

            # Prepare context for templates
            context = {
                'table': table,
                'table_snake_case': table_snake_case,
                'table_pascal_case': table_pascal_case,
                'table_kebab_case': table_kebab_case,
                'table_singular_kebab': table_singular_kebab,
                'table_plural_kebab': table_plural_kebab,
                'columns': list(table.columns.values()),
                'pk_column': self._get_pk_column(table),
                'pk_type': self._get_pk_type(table),
                'pk_name': self._get_pk_name(table),
            }

            # Generate View
            view_template = self.env.get_template("view.vue.j2")
            view_content = view_template.render(context)
            with open(os.path.join(base_path, "src", "views", f"{table_pascal_case}View.vue"), "w") as f:
                f.write(view_content)

            # Generate Service
            service_template = self.env.get_template("service.js.j2")
            service_content = service_template.render(context)
            with open(os.path.join(base_path, "src", "services", f"{table_snake_case}Service.js"), "w") as f:
                f.write(service_content)

            # Generate Store
            store_template = self.env.get_template("store.js.j2")
            store_content = store_template.render(context)
            with open(os.path.join(base_path, "src", "store", f"{table_snake_case}Store.js"), "w") as f:
                f.write(store_content)

            # Generate Test
            test_template = self.env.get_template("test.spec.js.j2")
            test_content = test_template.render(context)
            with open(os.path.join(base_path, "src", "tests", f"{table_snake_case}.spec.js"), "w") as f:
                f.write(test_content)

        # Generate common files
        common_context = {
            'tables': self.tables,
            'router_imports': [
                f"import {self._to_pascal_case(t.name)}View from '../views/{self._to_pascal_case(t.name)}View.vue'"
                for t in self.tables
            ],
            'router_routes': [
                f"{{ path: '/{self._pluralize(self._to_kebab_case(t.name))}', name: '{self._to_kebab_case(self._pluralize(t.name))}', component: {self._to_pascal_case(t.name)}View }}"
                for t in self.tables
            ],
            'store_imports': [
                f"import {{ {self._to_snake_case(t.name)}Store }} from './{self._to_snake_case(t.name)}Store'"
                for t in self.tables
            ],
            'store_exports': [
                f"{self._to_snake_case(t.name)}: {self._to_snake_case(t.name)}Store()"
                for t in self.tables
            ],
            'sidebar_links': [
                f"{{ label: '{self._pluralize(t.name).capitalize()}', to: '/{self._pluralize(self._to_kebab_case(t.name))}' }}"
                for t in self.tables
            ]
        }

        # Router config
        router_template = self.env.get_template("router.js.j2")
        with open(os.path.join(base_path, "src", "router", "index.js"), "w") as f:
            f.write(router_template.render(common_context))

        # Main App.vue
        app_vue_template = self.env.get_template("App.vue.j2")
        with open(os.path.join(base_path, "src", "App.vue"), "w") as f:
            f.write(app_vue_template.render(common_context))

        # Main JS entrypoint
        main_js_template = self.env.get_template("main.js.j2")
        with open(os.path.join(base_path, "src", "main.js"), "w") as f:
            f.write(main_js_template.render(common_context))

        # package.json
        package_json_template = self.env.get_template("package.json.j2")
        with open(os.path.join(base_path, "package.json"), "w") as f:
            f.write(package_json_template.render(common_context))

        # public/index.html
        index_html_template = self.env.get_template("index.html.j2")
        with open(os.path.join(base_path, "public", "index.html"), "w") as f:
            f.write(index_html_template.render(common_context))


        print(f"Frontend UI generated successfully in '{output_dir}' directory.")


# --- Placeholder Jinja2 Templates (These would typically be in templates/frontend/) ---

# view.vue.j2
VIEW_TEMPLATE = """
<template>
  <div class="p-grid p-fluid">
    <div class="p-col-12">
      <Card>
        <template #title>{{ table_pascal_case }} Management</template>
        <template #content>
          <DataTable :value="{{ table_snake_case | pluralize }}" :paginator="true" :rows="10"
                     v-model:selection="selected{{ table_pascal_case | pluralize }}" selectionMode="single" dataKey="{{ pk_name | snake_case }}"
                     @rowSelect="onRowSelect" @rowUnselect="onRowUnselect"
                     responsiveLayout="scroll">
            <Column selectionMode="single" headerStyle="width: 3em"></Column>
            {% for column in columns %}
            <Column field="{{ column.name | snake_case }}" header="{{ column.name | pascal_case }}" sortable></Column>
            {% endfor %}
            <Column header="Actions">
              <template #body="slotProps">
                <Button icon="pi pi-pencil" class="p-button-rounded p-button-success p-mr-2" @click="edit{{ table_pascal_case }}(slotProps.data)" />
                <Button icon="pi pi-trash" class="p-button-rounded p-button-warning" @click="confirmDelete{{ table_pascal_case }}(slotProps.data)" />
              </template>
            </Column>
          </DataTable>

          <Dialog v-model:visible="displayDialog" :style="{width: '450px'}" header="{{ table_pascal_case }} Details" :modal="true" class="p-fluid">
            <div class="p-field">
              <label for="{{ pk_name | snake_case }}">{{ pk_name | pascal_case }}</label>
              <InputText id="{{ pk_name | snake_case }}" v-model.trim="editItem.{{ pk_name | snake_case }}" required="true" autofocus :class="{'p-invalid': submitted && !editItem.{{ pk_name | snake_case }}}" :disabled="editMode" />
              <small class="p-invalid" v-if="submitted && !editItem.{{ pk_name | snake_case }}">ID is required.</small>
            </div>
            {% for column in columns %}
            {% if not column.is_primary %}
            <div class="p-field">
              <label for="{{ column.name | snake_case }}">{{ column.name | pascal_case }}</label>
              <InputText id="{{ column.name | snake_case }}" v-model.trim="editItem.{{ column.name | snake_case }}" />
            </div>
            {% endif %}
            {% endfor %}

            <template #footer>
              <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="hideDialog"/>
              <Button label="Save" icon="pi pi-check" class="p-button-text" @click="save{{ table_pascal_case }}"/>
            </template>
          </Dialog>

          <Dialog v-model:visible="deleteDialog" :style="{width: '450px'}" header="Confirm" :modal="true">
            <div class="confirmation-content">
              <i class="pi pi-exclamation-triangle p-mr-3" style="font-size: 2rem" />
              <span v-if="itemToDelete">Are you sure you want to delete the {{ table_snake_case }} with ID <b>{{ pk_name | pascal_case }}: {{ '{{ itemToDelete.' + pk_name | snake_case + ' }}' }}</b>?</span>
            </div>
            <template #footer>
              <Button label="No" icon="pi pi-times" class="p-button-text" @click="deleteDialog = false"/>
              <Button label="Yes" icon="pi pi-check" class="p-button-text" @click="delete{{ table_pascal_case }}"/>
            </template>
          </Dialog>

          <Button label="New {{ table_pascal_case }}" icon="pi pi-plus" class="p-button-success p-mt-3" @click="openNew" />
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { use{{ table_pascal_case }}Store } from '@/store/{{ table_snake_case }}Store';
import { storeToRefs } from 'pinia';
import { useToast } from 'primevue/usetoast';

const toast = useToast();
const {{ table_snake_case }}Store = use{{ table_pascal_case }}Store();
const { {{ table_snake_case | pluralize }} } = storeToRefs({{ table_snake_case }}Store);

const selected{{ table_pascal_case | pluralize }} = ref(null);
const displayDialog = ref(false);
const deleteDialog = ref(false);
const editMode = ref(false);
const submitted = ref(false);
const editItem = ref({});
const itemToDelete = ref(null);

onMounted(() => {
  {{ table_snake_case }}Store.fetch{{ table_pascal_case | pluralize }}();
});

const openNew = () => {
  editItem.value = {
    {% for column in columns %}
    {% if not column.is_primary %}
    {{ column.name | snake_case }}: {{ 'null' if column.nullable else '""' }},
    {% endif %}
    {% endfor %}
  };
  submitted.value = false;
  editMode.value = false;
  displayDialog.value = true;
};

const hideDialog = () => {
  displayDialog.value = false;
  submitted.value = false;
};

const save{{ table_pascal_case }} = async () => {
  submitted.value = true;
  if (editItem.value.{{ pk_name | snake_case }}) {
    // Update existing
    await {{ table_snake_case }}Store.update{{ table_pascal_case }}(editItem.value.{{ pk_name | snake_case }}, editItem.value);
    toast.add({severity:'success', summary: 'Successful', detail: '{{ table_pascal_case }} Updated', life: 3000});
  } else {
    // Create new
    await {{ table_snake_case }}Store.create{{ table_pascal_case }}(editItem.value);
    toast.add({severity:'success', summary: 'Successful', detail: '{{ table_pascal_case }} Created', life: 3000});
  }
  displayDialog.value = false;
  editItem.value = {};
};

const edit{{ table_pascal_case }} = (item) => {
  editItem.value = { ...item };
  editMode.value = true;
  displayDialog.value = true;
};

const confirmDelete{{ table_pascal_case }} = (item) => {
  itemToDelete.value = item;
  deleteDialog.value = true;
};

const delete{{ table_pascal_case }} = async () => {
  await {{ table_snake_case }}Store.delete{{ table_pascal_case }}(itemToDelete.value.{{ pk_name | snake_case }});
  deleteDialog.value = false;
  itemToDelete.value = null;
  toast.add({severity:'success', summary: 'Successful', detail: '{{ table_pascal_case }} Deleted', life: 3000});
};

const onRowSelect = (event) => {
  toast.add({severity: 'info', summary: '{{ table_pascal_case }} Selected', detail: `ID: ${event.data.{{ pk_name | snake_case }}}`, life: 3000});
};

const onRowUnselect = (event) => {
  toast.add({severity: 'warn', summary: '{{ table_pascal_case }} Unselected', detail: `ID: ${event.data.{{ pk_name | snake_case }}}`, life: 3000});
};
</script>

<style scoped>
/* Add component-specific styles here */
.p-field {
  margin-bottom: 1rem;
}
.confirmation-content {
  display: flex;
  align-items: center;
  padding: 1.5rem 0;
}
.confirmation-content i {
  margin-right: 0.5rem;
}
</style>
"""

# service.js.j2
SERVICE_TEMPLATE = """
import axios from 'axios';

const API_URL = 'http://localhost:8000/{{ table_snake_case | pluralize }}'; // Adjust if your backend runs on a different port/path

class {{ table_pascal_case }}Service {
  getAll() {
    return axios.get(API_URL);
  }

  get(id) {
    return axios.get(`${API_URL}/${id}`);
  }

  create(data) {
    return axios.post(API_URL, data);
  }

  update(id, data) {
    return axios.put(`${API_URL}/${id}`, data);
  }

  delete(id) {
    return axios.delete(`${API_URL}/${id}`);
  }
}

export default new {{ table_pascal_case }}Service();
"""

# store.js.j2
STORE_TEMPLATE = """
import { defineStore } from 'pinia';
import {{ table_pascal_case }}Service from '@/services/{{ table_snake_case }}Service';

export const use{{ table_pascal_case }}Store = defineStore('{{ table_snake_case }}', {
  state: () => ({
    {{ table_snake_case | pluralize }}: [],
    current{{ table_pascal_case }}: null,
    loading: false,
    error: null,
  }),
  actions: {
    async fetch{{ table_pascal_case | pluralize }}() {
      this.loading = true;
      try {
        const response = await {{ table_pascal_case }}Service.getAll();
        this.{{ table_snake_case | pluralize }} = response.data;
      } catch (err) {
        this.error = err;
        console.error('Error fetching {{ table_snake_case | pluralize }}:', err);
      } finally {
        this.loading = false;
      }
    },
    async fetch{{ table_pascal_case }}(id) {
      this.loading = true;
      try {
        const response = await {{ table_pascal_case }}Service.get(id);
        this.current{{ table_pascal_case }} = response.data;
      } catch (err) {
        this.error = err;
        console.error('Error fetching {{ table_snake_case }}:', err);
      } finally {
        this.loading = false;
      }
    },
    async create{{ table_pascal_case }}({{ table_snake_case }}Data) {
      this.loading = true;
      try {
        const response = await {{ table_pascal_case }}Service.create({{ table_snake_case }}Data);
        this.{{ table_snake_case | pluralize }}.push(response.data);
        return response.data;
      } catch (err) {
        this.error = err;
        console.error('Error creating {{ table_snake_case }}:', err);
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async update{{ table_pascal_case }}(id, {{ table_snake_case }}Data) {
      this.loading = true;
      try {
        const response = await {{ table_pascal_case }}Service.update(id, {{ table_snake_case }}Data);
        const index = this.{{ table_snake_case | pluralize }}.findIndex(item => item.{{ pk_name | snake_case }} === id);
        if (index !== -1) {
          this.{{ table_snake_case | pluralize }}[index] = response.data;
        }
        return response.data;
      } catch (err) {
        this.error = err;
        console.error('Error updating {{ table_snake_case }}:', err);
        throw err;
      } finally {
        this.loading = false;
      }
    },
    async delete{{ table_pascal_case }}(id) {
      this.loading = true;
      try {
        await {{ table_pascal_case }}Service.delete(id);
        this.{{ table_snake_case | pluralize }} = this.{{ table_snake_case | pluralize }}.filter(item => item.{{ pk_name | snake_case }} !== id);
      } catch (err) {
        this.error = err;
        console.error('Error deleting {{ table_snake_case }}:', err);
        throw err;
      } finally {
        this.loading = false;
      }
    },
  },
});
"""

# test.spec.js.j2
TEST_TEMPLATE = """
import { mount } from '@vue/test-utils';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {{ table_pascal_case }}View from '@/views/{{ table_pascal_case }}View.vue';
import { createPinia, setActivePinia } from 'pinia';
import {{ table_pascal_case }}Service from '@/services/{{ table_snake_case }}Service';
import PrimeVue from 'primevue/config';
import ToastService from 'primevue/toastservice';
import { useToast } from 'primevue/usetoast';

// Mock the service
vi.mock('@/services/{{ table_snake_case }}Service', () => ({
  default: {
    getAll: vi.fn(() => Promise.resolve({ data: [] })),
    get: vi.fn(() => Promise.resolve({ data: {} })),
    create: vi.fn(() => Promise.resolve({ data: {} })),
    update: vi.fn(() => Promise.resolve({ data: {} })),
    delete: vi.fn(() => Promise.resolve()),
  },
}));

// Mock PrimeVue useToast
vi.mock('primevue/usetoast', () => ({
  useToast: vi.fn(() => ({
    add: vi.fn(),
  })),
}));

describe('{{ table_pascal_case }}View', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  const createWrapper = () => mount({{ table_pascal_case }}View, {
    global: {
      plugins: [PrimeVue, ToastService],
      stubs: {
        Card: true,
        DataTable: true,
        Column: true,
        Button: true,
        Dialog: true,
        InputText: true,
        Toast: true,
      },
    },
  });

  it('renders without crashing', () => {
    const wrapper = createWrapper();
    expect(wrapper.exists()).toBe(true);
  });

  it('fetches {{ table_snake_case | pluralize }} on mount', async () => {
    const mockData = [{ {{ pk_name | snake_case }}: 1, {% for column in columns %}{% if not column.is_primary %}{{ column.name | snake_case }}: {{ column | get_default_js_value_for_type }}{% if not loop.last %}, {% endif %}{% endif %}{% endfor %} }];
    {{ table_pascal_case }}Service.getAll.mockResolvedValueOnce({ data: mockData });

    const wrapper = createWrapper();
    await vi.nextTick(); // Wait for onMounted hook to run

    expect({{ table_pascal_case }}Service.getAll).toHaveBeenCalledTimes(1);
    // Assert that the store's state is updated (requires accessing the store directly or checking rendered data)
    // For simplicity, we'll rely on the service mock being called.
  });

  it('opens new dialog and resets item', async () => {
    const wrapper = createWrapper();
    await wrapper.find('button.p-button-success').trigger('click'); // Click 'New {{ table_pascal_case }}' button

    expect(wrapper.vm.displayDialog).toBe(true);
    expect(wrapper.vm.editMode).toBe(false);
    {% for column in columns %}
    {% if not column.is_primary %}
    expect(wrapper.vm.editItem.{{ column.name | snake_case }}).toBe({{ 'null' if column.nullable else '""' }});
    {% endif %}
    {% endfor %}
  });

  it('saves a new {{ table_snake_case }}', async () => {
    const wrapper = createWrapper();
    const mockNewItem = { {% for column in columns %}{% if not column.is_primary %}{{ column.name | snake_case }}: {{ column | get_default_js_value_for_type }}{% if not loop.last %}, {% endif %}{% endif %}{% endfor %} };
    const mockCreatedItem = { {{ pk_name | snake_case }}: 1, ...mockNewItem };

    {{ table_pascal_case }}Service.create.mockResolvedValueOnce({ data: mockCreatedItem });
    const toastSpy = useToast().add;

    // Simulate opening dialog and setting data
    wrapper.vm.openNew();
    wrapper.vm.editItem = mockNewItem;
    
    await wrapper.vm.save{{ table_pascal_case }}();

    expect({{ table_pascal_case }}Service.create).toHaveBeenCalledWith(mockNewItem);
    expect(wrapper.vm.displayDialog).toBe(false);
    expect(toastSpy).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success', detail: '{{ table_pascal_case }} Created' }));
  });

  it('updates an existing {{ table_snake_case }}', async () => {
    const wrapper = createWrapper();
    const existingItem = { {{ pk_name | snake_case }}: 1, {% for column in columns %}{% if not column.is_primary %}{{ column.name | snake_case }}: {{ column | get_default_js_value_for_type }}{% if not loop.last %}, {% endif %}{% endif %}{% endfor %} };
    const updatedItemData = { {% for column in columns %}{% if not column.is_primary %}{{ column.name | snake_case }}: {{ column | get_default_js_value_for_type | replace('_test', '_updated') | replace('1', '2') | replace('1.0', '2.0') | replace('2024-01-01', '2024-01-02') | replace('12:00:00Z', '13:00:00Z') }}{% if not loop.last %}, {% endif %}{% endif %}{% endfor %} };
    const mockUpdatedItem = { {{ pk_name | snake_case }}: 1, ...updatedItemData };

    {{ table_pascal_case }}Service.update.mockResolvedValueOnce({ data: mockUpdatedItem });
    const toastSpy = useToast().add;

    // Simulate editing an item
    wrapper.vm.edit{{ table_pascal_case }}(existingItem);
    wrapper.vm.editItem = { ...existingItem, ...updatedItemData }; // Update the item in the dialog

    await wrapper.vm.save{{ table_pascal_case }}();

    expect({{ table_pascal_case }}Service.update).toHaveBeenCalledWith(existingItem.{{ pk_name | snake_case }}, expect.objectContaining(updatedItemData));
    expect(wrapper.vm.displayDialog).toBe(false);
    expect(toastSpy).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success', detail: '{{ table_pascal_case }} Updated' }));
  });

  it('deletes a {{ table_snake_case }}', async () => {
    const wrapper = createWrapper();
    const itemToDelete = { {{ pk_name | snake_case }}: 1, {% for column in columns %}{% if not column.is_primary %}{{ column.name | snake_case }}: {{ column | get_default_js_value_for_type }}{% if not loop.last %}, {% endif %}{% endif %}{% endfor %} };

    {{ table_pascal_case }}Service.delete.mockResolvedValueOnce({});
    const toastSpy = useToast().add;

    // Simulate confirming delete
    wrapper.vm.confirmDelete{{ table_pascal_case }}(itemToDelete);
    expect(wrapper.vm.deleteDialog).toBe(true);

    await wrapper.vm.delete{{ table_pascal_case }}();

    expect({{ table_pascal_case }}Service.delete).toHaveBeenCalledWith(itemToDelete.{{ pk_name | snake_case }});
    expect(wrapper.vm.deleteDialog).toBe(false);
    expect(toastSpy).toHaveBeenCalledWith(expect.objectContaining({ severity: 'success', detail: '{{ table_pascal_case }} Deleted' }));
  });
});
"""

# router.js.j2
ROUTER_TEMPLATE = """
import { createRouter, createWebHistory } from 'vue-router';
{% for router_import in router_imports %}
{{ router_import }}
{% endfor %}

const routes = [
  { path: '/', redirect: '/dashboard' }, // Redirect root to a dashboard or first table
  { path: '/dashboard', name: 'dashboard', component: { template: '<div>Dashboard Content</div>' } }, // Placeholder dashboard
  {% for route in router_routes %}
  {{ route }},
  {% endfor %}
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

export default router;
"""

# App.vue.j2
APP_VUE_TEMPLATE = """
<template>
  <div id="wrapper">
    <!-- Sidebar -->
    <Sidebar v-model:visible="sidebarVisible" :baseZIndex="999">
      <template #header>
        <h3>Admin Panel</h3>
      </template>
      <Menu :model="sidebarItems" />
    </Sidebar>

    <!-- Content Wrapper -->
    <div id="content-wrapper" class="d-flex flex-column">
      <!-- Main Content -->
      <div id="content">
        <!-- Topbar -->
        <Toolbar>
          <template #start>
            <Button icon="pi pi-bars" class="p-button-text" @click="toggleSidebar" />
          </template>
          <template #end>
            <Button icon="pi pi-user" class="p-button-rounded p-button-text" label="User" />
          </template>
        </Toolbar>

        <!-- Begin Page Content -->
        <div class="container-fluid p-4">
          <router-view />
        </div>
      </div>

      <!-- Footer -->
      <footer class="sticky-footer bg-white">
        <div class="container my-auto">
          <div class="copyright text-center my-auto">
            <span>Copyright &copy; Your App 2024</span>
          </div>
        </div>
      </footer>
    </div>
  </div>
  <Toast />
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import Sidebar from 'primevue/sidebar';
import Toolbar from 'primevue/toolbar';
import Button from 'primevue/button';
import Menu from 'primevue/menu';
import Toast from 'primevue/toast';

const router = useRouter();
const sidebarVisible = ref(false);

const toggleSidebar = () => {
  sidebarVisible.value = !sidebarVisible.value;
};

const sidebarItems = ref([
  {
    label: 'Dashboard',
    icon: 'pi pi-home',
    to: '/dashboard'
  },
  {
    label: 'Data Management',
    items: [
      {% for link in sidebar_links %}
      {{ link }},
      {% endfor %}
    ]
  }
]);
</script>

<style>
/* Basic SBAdmin-like styling (can be expanded with a proper CSS framework) */
#wrapper {
  display: flex;
}

#content-wrapper {
  flex-grow: 1;
  min-height: 100vh;
}

#content {
  flex-grow: 1;
}

.sticky-footer {
  padding: 1.5rem;
  flex-shrink: 0;
}

.p-toolbar {
  background-color: #f8f9fc;
  border-bottom: 1px solid #e3e6f0;
  padding: 1rem;
}

.p-sidebar .p-menu {
  width: 100%;
}

.p-sidebar .p-menu .p-menuitem-link {
  padding: 0.75rem 1.25rem;
}

/* PrimeVue overrides for a more Material/SBAdmin feel */
.p-button {
    border-radius: 0.5rem;
}

.p-card {
    border-radius: 0.75rem;
    box-shadow: 0 0.15rem 1.75rem 0 rgba(58, 59, 69, 0.15) !important;
}

.p-datatable .p-datatable-thead > tr > th {
    background-color: #f8f9fc;
    color: #858796;
    font-weight: bold;
}

.p-dialog .p-dialog-header {
    background-color: #4e73df;
    color: white;
    border-top-left-radius: 0.75rem;
    border-top-right-radius: 0.75rem;
}

.p-dialog .p-dialog-footer {
    border-top: 1px solid #dee2e6;
    padding-top: 1rem;
    text-align: right;
}

/* General layout */
.p-grid {
  display: flex;
  flex-wrap: wrap;
  margin-right: -0.5rem;
  margin-left: -0.5rem;
}

.p-col-12 {
  flex: 0 0 100%;
  max-width: 100%;
  padding-right: 0.5rem;
  padding-left: 0.5rem;
}

.p-mt-3 { margin-top: 1rem !important; }
.p-mr-2 { margin-right: 0.5rem !important; }
.p-mb-3 { margin-bottom: 1rem !important; }
.p-p-4 { padding: 1.5rem !important; }
</style>
"""

# main.js.j2
MAIN_JS_TEMPLATE = """
import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';

// PrimeVue
import PrimeVue from 'primevue/config';
import 'primevue/resources/themes/saga-blue/theme.css'; // or your preferred theme
import 'primevue/resources/primevue.min.css';
import 'primeicons/primeicons.css';
import ToastService from 'primevue/toastservice';

// PrimeVue Components (import only what you need)
import Button from 'primevue/button';
import Card from 'primevue/card';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Toolbar from 'primevue/toolbar';
import Sidebar from 'primevue/sidebar';
import Menu from 'primevue/menu';
import Toast from 'primevue/toast';


const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(PrimeVue);
app.use(ToastService);

// Register PrimeVue components globally
app.component('Button', Button);
app.component('Card', Card);
app.component('DataTable', DataTable);
app.component('Column', Column);
app.component('Dialog', Dialog);
app.component('InputText', InputText);
app.component('Toolbar', Toolbar);
app.component('Sidebar', Sidebar);
app.component('Menu', Menu);
app.component('Toast', Toast);


app.mount('#app');
"""

# package.json.j2
PACKAGE_JSON_TEMPLATE = """
{
  "name": "frontend",
  "version": "0.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test:unit": "vitest"
  },
  "dependencies": {
    "axios": "^1.7.2",
    "pinia": "^2.1.7",
    "primeicons": "^7.0.0",
    "primevue": "^3.52.0",
    "vue": "^3.4.21",
    "vue-router": "^4.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.4",
    "@vue/test-utils": "^2.4.5",
    "jsdom": "^24.0.0",
    "vite": "^5.2.8",
    "vitest": "^1.4.0"
  }
}
"""

# index.html.j2
INDEX_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <link rel="icon" href="/favicon.ico">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vue Admin Panel</title>
</head>
<body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
</body>
</html>
"""

# --- Example Usage (This part simulates how the generator would be used) ---
def create_template_files_frontend(template_dir="templates/frontend"):
    """Helper to create dummy template files for demonstration."""
    os.makedirs(template_dir, exist_ok=True)
    with open(os.path.join(template_dir, "view.vue.j2"), "w") as f:
        f.write(VIEW_TEMPLATE.strip())
    with open(os.path.join(template_dir, "service.js.j2"), "w") as f:
        f.write(SERVICE_TEMPLATE.strip())
    with open(os.path.join(template_dir, "store.js.j2"), "w") as f:
        f.write(STORE_TEMPLATE.strip())
    with open(os.path.join(template_dir, "test.spec.js.j2"), "w") as f:
        f.write(TEST_TEMPLATE.strip())
    with open(os.path.join(template_dir, "router.js.j2"), "w") as f:
        f.write(ROUTER_TEMPLATE.strip())
    with open(os.path.join(template_dir, "App.vue.j2"), "w") as f:
        f.write(APP_VUE_TEMPLATE.strip())
    with open(os.path.join(template_dir, "main.js.j2"), "w") as f:
        f.write(MAIN_JS_TEMPLATE.strip())
    with open(os.path.join(template_dir, "package.json.j2"), "w") as f:
        f.write(PACKAGE_JSON_TEMPLATE.strip())
    with open(os.path.join(template_dir, "index.html.j2"), "w") as f: # New template file
        f.write(INDEX_HTML_TEMPLATE.strip())
    print(f"Jinja2 frontend template files created in '{template_dir}'")

def main():
    # 1. Define your database schema using the provided classes
    user_id_col = Column(name="id")
    user_id_col.data_type = "integer"
    user_id_col.is_primary = True
    user_id_col.nullable = False

    user_name_col = Column(name="User Name") # Example with whitespace
    user_name_col.data_type = "varchar"
    user_name_col.char_length = 255
    user_name_col.nullable = False

    user_email_col = Column(name="email")
    user_email_col.data_type = "varchar"
    user_email_col.char_length = 255
    user_email_col.nullable = False
    user_email_col.constraints.append({"type": "UNIQUE", "name": "uq_user_email"})

    user_table = Table(name="users")
    user_table.columns["id"] = user_id_col
    user_table.columns["User Name"] = user_name_col # Use the name with whitespace
    user_table.columns["email"] = user_email_col
    user_table.primary_key = PrimaryKey(name="pk_users", columns=["id"])

    # You can add more tables here
    # product_table = Table(name="products")
    # ...

    tables_to_generate = [user_table]

    # 2. Ensure Jinja2 template directory exists with the template files
    create_template_files_frontend()

    # 3. Instantiate the generator
    generator = CRUDVueGenerator(tables=tables_to_generate)

    # 4. Generate the frontend
    generator.generate(output_dir="frontend")

if __name__ == "__main__":
    main()
