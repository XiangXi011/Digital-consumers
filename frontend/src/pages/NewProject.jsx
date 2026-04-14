import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';

const REVIEW_TYPE_CONFIG = {
  concept: {
    label: '新概念评审',
    desc: '验证新品概念是否“听得懂、觉得好、愿意买”',
    questionLabel: '本次想验证的商业问题',
    questionPlaceholder: '例如：这款儿童防蛀牙膏的新概念，能否提升首购意愿？',
    productLabel: '评审对象（产品定义）',
    productPlaceholder: '请填写：产品名称、核心功效、目标价格带、规格形态（如牙膏/漱口水）',
    briefLabel: '立项目标与成功标准（Business Brief）',
    briefPlaceholder: '请填写：业务目标、目标人群、竞品参照、希望优先优化的指标（如购买意愿/差异化）',
    copyLabel: '概念表达文案',
    copyPlaceholder: '请输入概念一句话、核心卖点描述、利益点表达（可选）',
    attachmentLabel: '概念素材上传（可选）',
    attachmentHint: '建议上传概念卡、卖点图、产品草图，便于模拟真实决策场景',
    fields: {
      product: true,
      brief: true,
      copy: false,
      attachments: true,
    },
    required: ['name', 'question', 'product', 'brief'],
  },
  packaging: {
    label: '包装设计评审',
    desc: '判断包装是否“看得见、看得懂、拿得起”',
    questionLabel: '本次想验证的包装问题',
    questionPlaceholder: '例如：新包装能否在3秒内传达“儿童温和防蛀”的核心价值？',
    productLabel: '评审对象（包装方案）',
    productPlaceholder: '请填写：包装版本、主视觉元素、关键文案区、应用渠道（货架/电商）',
    briefLabel: '包装评审背景（Business Brief）',
    briefPlaceholder: '请填写：品牌定位、目标人群、竞品参照、必须保留/必须规避的设计要素',
    copyLabel: '包装文案内容',
    copyPlaceholder: '请输入包装正背面核心文案（可选）',
    attachmentLabel: '包装稿件上传 *',
    attachmentHint: '建议上传平面稿/效果图/货架陈列图，支持多版本对比',
    fields: {
      product: true,
      brief: true,
      copy: false,
      attachments: true,
    },
    required: ['name', 'question', 'product', 'brief'],
  },
  copywriting: {
    label: '营销文案评审',
    desc: '评估文案是否“有记忆点、可信任、能转化”',
    questionLabel: '本次想验证的文案问题',
    questionPlaceholder: '例如：这组抖音投放文案是否能提升点击与加购意愿？',
    productLabel: '评审对象（产品与场景）',
    productPlaceholder: '请填写：产品信息、投放场景、目标转化动作（点击/加购/下单）',
    briefLabel: '传播任务背景（Business Brief）',
    briefPlaceholder: '请填写：目标受众、传播目标、竞品声音、内容边界（合规/语气）',
    copyLabel: '待评审文案 *',
    copyPlaceholder: '请粘贴标题、正文、卖点句、CTA（可一次输入多版本）',
    attachmentLabel: '文案素材上传（可选）',
    attachmentHint: '可上传落地页、海报、脚本等辅助材料',
    fields: {
      product: true,
      brief: true,
      copy: true,
      attachments: true,
    },
    required: ['name', 'question', 'product', 'copy'],
  },
  ab_test: {
    label: 'A/B 对比测试',
    desc: '比较两个方案在关键决策指标上的胜负与原因',
    questionLabel: '本次A/B决策问题',
    questionPlaceholder: '例如：A/B 两版主视觉，哪一版更能提升“首购意愿 + 专业信任感”？',
    productLabel: '对比对象说明',
    productPlaceholder: '请填写：A/B 对比维度（视觉/标题/利益点）、投放场景、目标人群',
    briefLabel: '对比规则与判定口径（Business Brief）',
    briefPlaceholder: '请填写：主要判定指标、次要指标、平票时优先级、业务约束',
    copyLabel: 'A/B 方案文案（建议必填）',
    copyPlaceholder: '建议按“【A】...【B】...”格式输入，突出差异点',
    attachmentLabel: 'A/B 素材上传（强烈建议）',
    attachmentHint: '建议同时上传 A 与 B 的原稿，系统会结合素材进行对比判断',
    fields: {
      product: true,
      brief: true,
      copy: true,
      attachments: true,
    },
    required: ['name', 'question', 'product'],
  },
};

const REVIEW_TYPE_OPTIONS = Object.entries(REVIEW_TYPE_CONFIG).map(([value, cfg]) => ({
  value,
  ...cfg,
}));

export default function NewProject() {
  const navigate = useNavigate();
  const [projectType, setProjectType] = useState('');
  const [personas, setPersonas] = useState([]);
  const [selectedPersonas, setSelectedPersonas] = useState([]);
  const [formData, setFormData] = useState({ name: '', brief: '', product: '', copy: '', question: '' });
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [enableGroupDiscussion, setEnableGroupDiscussion] = useState(false);
  const [enableDeepDive, setEnableDeepDive] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const activeTypeConfig = projectType ? REVIEW_TYPE_CONFIG[projectType] : null;

  // 从 URL 参数读取类型
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const type = params.get('type');
    if (type && REVIEW_TYPE_CONFIG[type]) setProjectType(type);
  }, []);

  // 加载真实画像列表
  useEffect(() => {
    api.getPersonas()
      .then(res => setPersonas(res.personas || []))
      .catch(err => console.error('Failed to load personas:', err));
  }, []);

  const togglePersona = (id) => {
    setSelectedPersonas(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedPersonas.length === personas.length) {
      setSelectedPersonas([]);
    } else {
      setSelectedPersonas(personas.map(p => p.id));
    }
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    for (const file of files) {
      try {
        const res = await api.uploadFile(file);
        setUploadedFiles(prev => [...prev, res]);
      } catch (err) {
        alert(`上传失败: ${err.message}`);
      }
    }
    e.target.value = '';
  };

  const fileMeta = (nameOrUrl = '') => {
    const text = String(nameOrUrl).toLowerCase();
    if (/(\.png|\.jpg|\.jpeg|\.webp|\.gif)$/.test(text)) return { icon: 'image', label: '图片' };
    if (/\.pdf$/.test(text)) return { icon: 'picture_as_pdf', label: 'PDF' };
    if (/(\.doc|\.docx)$/.test(text)) return { icon: 'description', label: '文档' };
    return { icon: 'attach_file', label: '附件' };
  };

  const copyLink = async (url) => {
    try {
      const absolute = url.startsWith('http') ? url : `${window.location.origin}${url}`;
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(absolute);
      }
      alert('附件链接已复制');
    } catch {
      alert('复制失败，请手动复制链接');
    }
  };

  const validateForm = () => {
    if (!projectType || !activeTypeConfig) {
      alert('请先选择评审类型');
      return false;
    }

    for (const field of activeTypeConfig.required) {
      if (!String(formData[field] || '').trim()) {
        const fieldLabelMap = {
          name: '项目名称',
          question: activeTypeConfig.questionLabel || '核心研究问题',
          product: '产品信息',
          brief: '背景描述 / Business Brief',
          copy: '测试文案',
        };
        alert(`请填写：${fieldLabelMap[field] || field}`);
        return false;
      }
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;

    setSubmitting(true);
    try {
      const res = await api.createProject({
        name: formData.name,
        project_type: projectType,
        persona_ids: selectedPersonas,
        business_brief: formData.brief,
        product_info: formData.product,
        copy_material: formData.copy,
        user_question: formData.question || formData.name,
        attachments: uploadedFiles.map(f => f.relative_path || f.file_id || f.path),
        mode: selectedPersonas.length === 1 ? 'single' : 'multi',
        enable_group_discussion: enableGroupDiscussion,
        enable_deep_dive: enableDeepDive,
      });
      await api.runProject(res.session_id);
      navigate(`/projects/${res.session_id}`);
    } catch (err) {
      alert(`创建失败: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };


  return (
    <div className="pt-8 pb-12 px-8 h-full max-w-5xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-extrabold text-on-surface tracking-tight mb-2">新建评审项目</h2>
        <p className="text-sm text-on-surface-variant">仅支持口腔行业。请先选择评审类型，再填写对应信息。</p>
      </div>

      {!projectType ? (
        <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm border border-outline-variant/10">
          <h3 className="text-sm font-bold text-primary mb-4 flex items-center uppercase tracking-widest">
            <span className="material-symbols-outlined mr-2 text-[18px]">category</span>
            第一步：选择评审类型
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {REVIEW_TYPE_OPTIONS.map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => setProjectType(type.value)}
                className="text-left bg-surface border border-outline-variant/20 rounded-xl p-5 hover:border-primary/50 hover:bg-primary/5 transition-colors"
              >
                <p className="text-sm font-bold text-on-surface mb-1">{type.label}</p>
                <p className="text-xs text-on-surface-variant">{type.desc}</p>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-surface-container-lowest p-8 rounded-2xl shadow-sm border border-outline-variant/10">
          <form className="space-y-8" onSubmit={handleSubmit}>
            {/* 基本信息 */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-primary flex items-center uppercase tracking-widest">
                  <span className="material-symbols-outlined mr-2 text-[18px]">info</span>
                  基本信息
                </h3>
                <button
                  type="button"
                  onClick={() => setProjectType('')}
                  className="text-xs text-primary font-bold hover:underline"
                >
                  重新选择类型
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-xs font-bold text-on-surface-variant mb-2">项目名称 *</label>
                  <input type="text"
                    className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none"
                    placeholder="例如：舒客儿童牙膏夏季新品概念测试"
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-on-surface-variant mb-2">评审类型 *</label>
                  <div className="w-full bg-surface px-4 py-3 rounded-xl border border-primary/30 text-sm">
                    {activeTypeConfig?.label}
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <label className="block text-xs font-bold text-on-surface-variant mb-2">{activeTypeConfig?.questionLabel || '核心研究问题'} *</label>
                <input type="text"
                  className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none"
                  placeholder={activeTypeConfig?.questionPlaceholder || '请输入核心研究问题'}
                  value={formData.question}
                  onChange={e => setFormData({ ...formData, question: e.target.value })}
                />
              </div>
            </section>

            {/* 目标人群 — 加载真实画像 */}
            <section>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-primary flex items-center uppercase tracking-widest">
                  <span className="material-symbols-outlined mr-2 text-[18px]">groups</span>
                  目标数字画像
                </h3>
                <button type="button" onClick={selectAll} className="text-xs text-primary font-bold hover:underline">
                  {selectedPersonas.length === personas.length ? '取消全选' : '全选'}
                </button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {personas.map((persona) => (
                  <label key={persona.id} className="cursor-pointer group" onClick={() => togglePersona(persona.id)}>
                    <div className={`relative border-2 rounded-xl p-4 transition-colors h-full flex flex-col justify-between ${
                      selectedPersonas.includes(persona.id) ? 'border-primary bg-primary/5' : 'border-outline-variant/20 hover:border-primary/50'
                    }`}>
                      <input type="checkbox" checked={selectedPersonas.includes(persona.id)} readOnly
                        className="absolute top-4 right-4 w-4 h-4 text-primary rounded focus:ring-primary accent-primary" />
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 block mb-1">{persona.id}</span>
                        <span className="text-sm font-bold text-on-surface block">{persona.name}</span>
                      </div>
                      {persona.tags.length > 0 && (
                        <span className="inline-block mt-3 px-2 py-1 bg-surface-container text-[10px] font-bold text-on-surface-variant rounded w-max">
                          {persona.tags[0]}
                        </span>
                      )}
                    </div>
                  </label>
                ))}
              </div>
            </section>

            {/* 研究物料 */}
            <section>
              <h3 className="text-sm font-bold text-primary mb-4 flex items-center uppercase tracking-widest">
                <span className="material-symbols-outlined mr-2 text-[18px]">attachment</span>
                研究背景与物料
              </h3>
              <div className="space-y-4">
                {activeTypeConfig?.fields.product && (
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-2">
                      {activeTypeConfig.productLabel || '产品信息'} {activeTypeConfig.required.includes('product') ? '*' : ''}
                    </label>
                    <textarea rows={3}
                      className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none resize-none"
                      placeholder={activeTypeConfig.productPlaceholder || '请输入口腔产品名称、功效卖点、规格、价格带等...'}
                      value={formData.product} onChange={e => setFormData({ ...formData, product: e.target.value })}
                    ></textarea>
                  </div>
                )}

                {activeTypeConfig?.fields.brief && (
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-2">
                      {activeTypeConfig.briefLabel || '背景描述 / Business Brief'} {activeTypeConfig.required.includes('brief') ? '*' : ''}
                    </label>
                    <textarea rows={3}
                      className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none resize-none"
                      placeholder={activeTypeConfig.briefPlaceholder || '请输入项目背景、目标人群、核心竞争点、研究关注点...'}
                      value={formData.brief} onChange={e => setFormData({ ...formData, brief: e.target.value })}
                    ></textarea>
                  </div>
                )}

                {activeTypeConfig?.fields.copy && (
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-2">
                      {activeTypeConfig.copyLabel || '测试文案'} {activeTypeConfig.required.includes('copy') ? '*' : ''}
                    </label>
                    <textarea rows={4}
                      className="w-full bg-surface px-4 py-3 rounded-xl border border-outline-variant/30 focus:border-primary focus:ring-2 focus:ring-primary/20 transition-all text-sm outline-none resize-none"
                      placeholder={activeTypeConfig.copyPlaceholder || '请输入需要评审的标题、卖点文案、落地页文案等...'}
                      value={formData.copy} onChange={e => setFormData({ ...formData, copy: e.target.value })}
                    ></textarea>
                  </div>
                )}

                {activeTypeConfig?.fields.attachments && (
                  <div>
                    <label className="block text-xs font-bold text-on-surface-variant mb-2">
                      {activeTypeConfig.attachmentLabel || '上传测试物料 (图片/文档)'}
                    </label>
                    <div className="w-full border-2 border-dashed border-outline-variant/30 rounded-xl p-8 flex flex-col items-center justify-center bg-surface/50 hover:bg-surface hover:border-primary/50 transition-colors cursor-pointer group"
                      onClick={() => document.getElementById('file-input').click()}>
                      <input id="file-input" type="file" multiple className="hidden" accept=".jpg,.jpeg,.png,.webp,.gif,.pdf,.doc,.docx" onChange={handleFileUpload} />
                      <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                        <span className="material-symbols-outlined text-primary">upload_file</span>
                      </div>
                      <span className="text-sm font-bold text-on-surface mb-1">点击或拖拽文件至此处</span>
                      <span className="text-xs text-slate-400">{activeTypeConfig.attachmentHint || '支持 PDF, JPG, PNG (最大 10MB)'}</span>
                    </div>
                    {uploadedFiles.length > 0 && (
                      <div className="mt-3 space-y-1">
                        {uploadedFiles.map((f, i) => (
                          <div key={i} className="flex items-center text-xs text-emerald-600 bg-emerald-50 px-3 py-1.5 rounded-lg">
                            <span className="material-symbols-outlined text-sm mr-2">check_circle</span>
                            {f.filename} ({(f.size / 1024).toFixed(1)} KB)
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>

            {/* Research methodology toggles */}
            <section>
              <h3 className="text-sm font-bold text-primary mb-4 flex items-center uppercase tracking-widest">
                <span className="material-symbols-outlined mr-2 text-[18px]">science</span>
                研究方法增强
              </h3>
              <div className="space-y-3">
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableGroupDiscussion}
                    onChange={e => setEnableGroupDiscussion(e.target.checked)}
                    className="w-4 h-4 text-primary rounded accent-primary"
                  />
                  <div>
                    <span className="text-sm font-semibold text-on-surface">焦点小组讨论</span>
                    <p className="text-xs text-on-surface-variant">模拟 3-4 位消费者进行结构化辩论，发现共识与分歧</p>
                  </div>
                </label>
                <label className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enableDeepDive}
                    onChange={e => setEnableDeepDive(e.target.checked)}
                    className="w-4 h-4 text-primary rounded accent-primary"
                  />
                  <div>
                    <span className="text-sm font-semibold text-on-surface">深度访谈</span>
                    <p className="text-xs text-on-surface-variant">对持不同立场的消费者进行深度探询（需先启用焦点讨论）</p>
                  </div>
                </label>
              </div>
            </section>

            {/* Actions */}
            <div className="pt-6 border-t border-outline-variant/10 flex justify-end space-x-4">
              <a href="/" className="px-6 py-3 rounded-xl text-sm font-bold text-on-surface-variant hover:bg-surface-container transition-colors">取消</a>
              <button type="submit" disabled={submitting}
                className="px-8 py-3 rounded-xl text-sm font-bold bg-primary text-white shadow-md hover:shadow-lg hover:bg-primary/90 transition-all active:scale-[0.98] flex items-center disabled:opacity-50">
                <span className="material-symbols-outlined mr-2 text-[18px]">rocket_launch</span>
                {submitting ? '创建中...' : '发起评审'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
