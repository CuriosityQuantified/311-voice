import { createRoot } from 'react-dom/client'
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";
import './index.css'
import Preview from './Preview'

createRoot(document.getElementById('root')!).render(
  <CopilotKit runtimeUrl="http://localhost:8000/api/copilotkit">
    <Preview />
  </CopilotKit>
)
