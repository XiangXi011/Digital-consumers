export default function PersonaSelector({ personas, selected, onToggle, onSelectAll }) {
  const allSelected = selected.length === personas.length;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-primary flex items-center uppercase tracking-widest">
          <span className="material-symbols-outlined mr-2 text-[18px]">groups</span>
          目标数字画像
        </h3>
        <button type="button" onClick={onSelectAll} className="text-xs text-primary font-bold hover:underline">
          {allSelected ? '取消全选' : '全选'}
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {personas.map((persona) => {
          const isSelected = selected.includes(persona.id);
          return (
            <label key={persona.id} className="cursor-pointer group" onClick={() => onToggle(persona.id)}>
              <div className={`relative border-2 rounded-xl p-4 transition-colors h-full flex flex-col justify-between ${
                isSelected ? 'border-primary bg-primary/5' : 'border-outline-variant/20 hover:border-primary/50'
              }`}>
                <input type="checkbox" checked={isSelected} readOnly
                  className="absolute top-4 right-4 w-4 h-4 text-primary rounded focus:ring-primary accent-primary" />
                <div>
                  <span className="text-xs font-bold text-slate-400 block mb-1">{persona.id}</span>
                  <span className="text-sm font-bold text-on-surface block">{persona.name}</span>
                </div>
                {persona.budget_band && (
                  <span className="inline-block mt-2 px-2 py-0.5 bg-surface-container text-xs font-bold text-on-surface-variant rounded w-max">
                    {persona.budget_band}
                  </span>
                )}
                {persona.veto_trigger && (
                  <p className="text-xs text-red-500 mt-1 truncate" title={persona.veto_trigger}>
                    Veto: {persona.veto_trigger}
                  </p>
                )}
                {persona.tags?.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {persona.tags.slice(0, 2).map((tag) => (
                      <span key={tag} className="inline-block px-2 py-0.5 bg-surface-container text-xs font-bold text-on-surface-variant rounded">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}
