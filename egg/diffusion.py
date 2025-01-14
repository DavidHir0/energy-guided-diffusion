import torch
import torch.nn as nn
from egg.guided_diffusion.script_util import (
    create_model_and_diffusion,
    model_and_diffusion_defaults,
)


class EGG(nn.Module):
    def __init__(
        self,
        diffusion_artefact="./models/256x256_diffusion_uncond.pt",
        config=None,
        num_steps=50,
    ):
        super().__init__()
        # Model settings
        device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

        self.model_config = model_and_diffusion_defaults()
        self.model_config.update(
            {
                "attention_resolutions": "32, 16, 8",
                "class_cond": False,
                "diffusion_steps": 1000,
                "rescale_timesteps": True,
                "timestep_respacing": f"{num_steps}",
                "image_size": 256,
                "learn_sigma": True,
                "noise_schedule": "linear",
                "num_channels": 256,
                "num_head_channels": 64,
                "num_res_blocks": 2,
                "resblock_updown": True,
                "use_checkpoint": False,
                "use_fp16": True,
                "use_scale_shift_norm": True,
            }
        )

        if config is not None:
            self.model_config.update(config)

        self.model, self.diffusion = create_model_and_diffusion(**self.model_config)
        self.model.load_state_dict(torch.load(diffusion_artefact, map_location="cpu"))
        self.model.requires_grad_(True).eval().to(device)
        if self.model_config["use_fp16"]:
            self.model.convert_to_fp16()

    def sample(
        self,
        energy_fn,
        energy_scale=1,
        num_samples=1,
        *,
        use_alpha_bar=False,
        normalize_grad=True
    ):
        """
        This function samples from a diffusion model using a given energy function and other optional parameters.

        :param energy_fn: The energy function used to calculate the energy of the samples generated by the model. It takes
        in the generated samples and returns a dict of energies of the samples
        :param energy_scale: The energy scale is a parameter that scales the energy function used in the sampling process.
        It can be used to adjust the importance of the energy function relative to other factors in the sampling process. A
        higher energy scale will result in a stronger influence of the energy function on the samples generated, defaults to
        1 (optional)
        :param num_samples: The number of samples to generate, defaults to 1 (optional)
        :param use_alpha_bar: use_alpha_bar is a boolean parameter that determines whether to use the alpha-bar
        regularization term during sampling. If set to True, the alpha-bar regularization term will be used. If set to
        False, it will not be used, defaults to False (optional)
        :param normalize_grad: A boolean parameter that determines whether to normalize the gradient of the energy function
        during sampling. If set to True, the gradient will be normalized to have unit norm. This can help with stability
        during sampling. If set to False, the gradient will not be normalized, defaults to True (optional)
        :return: a set of samples generated using the progressive sampling loop of the diffusion model. The samples are
        generated based on the given energy function and energy scale, and the number of samples is determined by the
        `num_samples` parameter. The samples are returned as a tensor of shape `(num_samples, 3, image_size, image_size)`.
        The function also has optional parameters for using alpha
        """
        return self.diffusion.p_sample_loop_progressive(
            self.model,
            (
                num_samples,
                3,
                self.model_config["image_size"],
                self.model_config["image_size"],
            ),
            clip_denoised=False,
            model_kwargs={},
            progress=True,
            energy_fn=energy_fn,
            energy_scale=energy_scale,
            use_alpha_bar=use_alpha_bar,
            normalize_grad=normalize_grad,
        )
