const fs = require('fs');
let content = fs.readFileSync('frontend/src/pages/StudioPage.tsx', 'utf-8');

const outputOld = `                  {/* Output */}
                  <div className="p-5 min-h-[360px] flex flex-col bg-slate-50/30">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-2 mb-3">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="ui-label mb-0">Output</span>
                        {batchJobIds.length > 1 && batchJobIndex >= 0 && (
                          <span className="text-[10px] font-semibold tabular-nums text-slate-500">
                            Job {batchJobIndex + 1}/{batchJobIds.length}
                          </span>
                        )}
                      </div>`;
const outputNew = `                  </div>
                  {/* Generated Card */}
                  <div className="flex flex-col bg-white rounded-xl border border-gray-200 overflow-hidden min-h-[400px]">
                    <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100 bg-white shrink-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-gray-900">GENERATED IMAGE</span>
                        <Info className="size-3.5 text-gray-400" />
                      </div>
                      {activeJob?.status === "COMPLETED" ? (
                        <span className="flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider text-emerald-700">
                          <Sparkles className="size-3 text-emerald-500" />
                          Completed
                        </span>
                      ) : (
                        batchJobIds.length > 1 && batchJobIndex >= 0 && (
                          <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500">
                            Job {batchJobIndex + 1}/{batchJobIds.length}
                          </span>
                        )
                      )}
                    </div>
                    <div className="flex-1 bg-[var(--jewel-bg)] relative flex flex-col p-4">`;
content = content.replace(outputOld, outputNew);

const actionDockTarget = `              <ActionDock`;
const actionDockReplacement = `                    </div>
                  </div>
              <ActionDock`;
content = content.replace(actionDockTarget, actionDockReplacement);

const endTarget = `              </div>
            </>
          </section>`;
const endReplacement = `              </div>
            </>
            </div>
          </section>`;
content = content.replace(endTarget, endReplacement);

fs.writeFileSync('frontend/src/pages/StudioPage.tsx', content);
