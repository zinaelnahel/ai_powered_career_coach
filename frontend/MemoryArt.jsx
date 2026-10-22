import { DojoIcon } from './DojoIcons.jsx';

export function MemoryIcon({ name = 'spark', className = '' }) {
  return <DojoIcon name={name} className={`memory-icon ${className}`} />;
}
